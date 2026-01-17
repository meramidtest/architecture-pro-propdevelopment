#!/usr/bin/env python3
"""
Скрипт для фильтрации подозрительных событий из Kubernetes Audit Log.

Выявляет:
1. Доступ к secrets (get/list)
2. kubectl exec в поды
3. Создание привилегированных подов
4. Создание RoleBinding/ClusterRoleBinding с cluster-admin
5. Доступ к логам системных подов (kube-apiserver, etcd и т.д.)
6. Удаление или изменение критических ресурсов
"""

import json
import sys
from typing import Dict, List, Any
from datetime import datetime


def load_audit_events(filepath: str) -> List[Dict]:
    """Загружает JSON события из audit.log."""
    events = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('{'):
                try:
                    event = json.loads(line)
                    if event.get('kind') == 'Event' and event.get('apiVersion', '').startswith('audit.k8s.io'):
                        events.append(event)
                except json.JSONDecodeError:
                    continue
    return events


def is_system_user(username: str) -> bool:
    """Проверяет, является ли пользователь системным."""
    system_prefixes = [
        'system:apiserver',
        'system:kube-scheduler',
        'system:kube-controller-manager',
        'system:node:',
        'system:serviceaccount:kube-system:'
    ]
    return any(username.startswith(prefix) for prefix in system_prefixes)


def filter_secrets_access(events: List[Dict]) -> List[Dict]:
    """Фильтрует события доступа к secrets."""
    suspicious = []
    for event in events:
        obj_ref = event.get('objectRef', {})
        verb = event.get('verb', '')
        user = event.get('user', {}).get('username', '')
        stage = event.get('stage', '')

        if (obj_ref.get('resource') == 'secrets' and
            verb in ['get', 'list'] and
            stage == 'ResponseComplete' and
            not is_system_user(user)):
            suspicious.append({
                'type': 'secrets_access',
                'event': event,
                'summary': {
                    'user': user,
                    'verb': verb,
                    'namespace': obj_ref.get('namespace', 'cluster-wide'),
                    'secret_name': obj_ref.get('name', 'all'),
                    'timestamp': event.get('requestReceivedTimestamp'),
                    'response_code': event.get('responseStatus', {}).get('code')
                }
            })
    return suspicious


def filter_exec_events(events: List[Dict]) -> List[Dict]:
    """Фильтрует события kubectl exec."""
    suspicious = []
    for event in events:
        obj_ref = event.get('objectRef', {})
        user = event.get('user', {}).get('username', '')
        stage = event.get('stage', '')

        if (obj_ref.get('subresource') == 'exec' and
            stage == 'ResponseComplete' and
            not is_system_user(user)):
            # Извлекаем команду из requestURI
            request_uri = event.get('requestURI', '')
            suspicious.append({
                'type': 'kubectl_exec',
                'event': event,
                'summary': {
                    'user': user,
                    'pod_name': obj_ref.get('name'),
                    'namespace': obj_ref.get('namespace'),
                    'request_uri': request_uri,
                    'timestamp': event.get('requestReceivedTimestamp'),
                    'response_code': event.get('responseStatus', {}).get('code')
                }
            })
    return suspicious


def filter_privileged_pods(events: List[Dict]) -> List[Dict]:
    """Фильтрует события создания привилегированных подов."""
    suspicious = []
    for event in events:
        obj_ref = event.get('objectRef', {})
        verb = event.get('verb', '')
        user = event.get('user', {}).get('username', '')
        stage = event.get('stage', '')
        request_obj = event.get('requestObject', {})

        if (obj_ref.get('resource') == 'pods' and
            verb == 'create' and
            stage == 'ResponseComplete' and
            not is_system_user(user)):

            # Проверяем privileged контейнеры
            containers = request_obj.get('spec', {}).get('containers', [])
            for container in containers:
                sec_context = container.get('securityContext', {})
                if sec_context.get('privileged') == True:
                    suspicious.append({
                        'type': 'privileged_pod',
                        'event': event,
                        'summary': {
                            'user': user,
                            'pod_name': obj_ref.get('name'),
                            'namespace': obj_ref.get('namespace'),
                            'container_name': container.get('name'),
                            'image': container.get('image'),
                            'timestamp': event.get('requestReceivedTimestamp'),
                            'response_code': event.get('responseStatus', {}).get('code')
                        }
                    })
                    break
    return suspicious


def filter_rbac_escalation(events: List[Dict]) -> List[Dict]:
    """Фильтрует события создания RoleBinding с cluster-admin."""
    suspicious = []
    for event in events:
        obj_ref = event.get('objectRef', {})
        verb = event.get('verb', '')
        user = event.get('user', {}).get('username', '')
        stage = event.get('stage', '')
        request_obj = event.get('requestObject', {})

        if (obj_ref.get('resource') in ['rolebindings', 'clusterrolebindings'] and
            verb == 'create' and
            stage == 'ResponseComplete' and
            not is_system_user(user)):

            role_ref = request_obj.get('roleRef', {})
            if role_ref.get('name') == 'cluster-admin':
                subjects = request_obj.get('subjects', [])
                suspicious.append({
                    'type': 'rbac_escalation',
                    'event': event,
                    'summary': {
                        'user': user,
                        'binding_name': obj_ref.get('name'),
                        'namespace': obj_ref.get('namespace'),
                        'role': role_ref.get('name'),
                        'subjects': [{'kind': s.get('kind'), 'name': s.get('name'), 'namespace': s.get('namespace')} for s in subjects],
                        'timestamp': event.get('requestReceivedTimestamp'),
                        'response_code': event.get('responseStatus', {}).get('code')
                    }
                })
    return suspicious


def filter_system_pod_access(events: List[Dict]) -> List[Dict]:
    """Фильтрует события доступа к системным подам (логи, exec)."""
    suspicious = []
    system_pods = ['kube-apiserver', 'etcd', 'kube-controller-manager', 'kube-scheduler']

    for event in events:
        obj_ref = event.get('objectRef', {})
        user = event.get('user', {}).get('username', '')
        stage = event.get('stage', '')
        subresource = obj_ref.get('subresource', '')
        pod_name = obj_ref.get('name', '')

        if (obj_ref.get('resource') == 'pods' and
            subresource in ['log', 'exec'] and
            stage == 'ResponseComplete' and
            obj_ref.get('namespace') == 'kube-system' and
            not is_system_user(user)):

            # Проверяем, является ли под системным
            if any(sys_pod in pod_name for sys_pod in system_pods):
                suspicious.append({
                    'type': 'system_pod_access',
                    'event': event,
                    'summary': {
                        'user': user,
                        'pod_name': pod_name,
                        'namespace': obj_ref.get('namespace'),
                        'access_type': subresource,
                        'timestamp': event.get('requestReceivedTimestamp'),
                        'response_code': event.get('responseStatus', {}).get('code')
                    }
                })
    return suspicious


def filter_suspicious_pods(events: List[Dict]) -> List[Dict]:
    """Фильтрует создание подов с подозрительными именами."""
    suspicious = []
    suspicious_names = ['attacker', 'hack', 'pwn', 'exploit', 'malicious']

    for event in events:
        obj_ref = event.get('objectRef', {})
        verb = event.get('verb', '')
        user = event.get('user', {}).get('username', '')
        stage = event.get('stage', '')
        pod_name = obj_ref.get('name', '')

        if (obj_ref.get('resource') == 'pods' and
            verb == 'create' and
            stage == 'ResponseComplete' and
            not is_system_user(user)):

            if any(sus_name in pod_name.lower() for sus_name in suspicious_names):
                request_obj = event.get('requestObject', {})
                containers = request_obj.get('spec', {}).get('containers', [])
                suspicious.append({
                    'type': 'suspicious_pod_name',
                    'event': event,
                    'summary': {
                        'user': user,
                        'pod_name': pod_name,
                        'namespace': obj_ref.get('namespace'),
                        'containers': [{'name': c.get('name'), 'image': c.get('image')} for c in containers],
                        'timestamp': event.get('requestReceivedTimestamp'),
                        'response_code': event.get('responseStatus', {}).get('code')
                    }
                })
    return suspicious


def main():
    if len(sys.argv) < 2:
        print("Использование: python filter_audit.py <audit.log> [output.json]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'audit-extract.json'

    print(f"Загрузка событий из {input_file}...")
    events = load_audit_events(input_file)
    print(f"Загружено {len(events)} событий аудита")

    all_suspicious = []

    # Применяем фильтры
    print("\nПоиск подозрительных событий...")

    secrets = filter_secrets_access(events)
    print(f"  - Доступ к secrets: {len(secrets)}")
    all_suspicious.extend(secrets)

    exec_events = filter_exec_events(events)
    print(f"  - kubectl exec: {len(exec_events)}")
    all_suspicious.extend(exec_events)

    privileged = filter_privileged_pods(events)
    print(f"  - Привилегированные поды: {len(privileged)}")
    all_suspicious.extend(privileged)

    rbac = filter_rbac_escalation(events)
    print(f"  - RBAC эскалация: {len(rbac)}")
    all_suspicious.extend(rbac)

    system_access = filter_system_pod_access(events)
    print(f"  - Доступ к системным подам: {len(system_access)}")
    all_suspicious.extend(system_access)

    suspicious_pods = filter_suspicious_pods(events)
    print(f"  - Подозрительные имена подов: {len(suspicious_pods)}")
    all_suspicious.extend(suspicious_pods)

    # Сохраняем результат
    print(f"\nВсего подозрительных событий: {len(all_suspicious)}")

    # Сортируем по времени
    all_suspicious.sort(key=lambda x: x.get('summary', {}).get('timestamp', ''))

    # Создаем выходной файл
    output = {
        'generated_at': datetime.now().isoformat(),
        'source_file': input_file,
        'total_events': len(events),
        'suspicious_count': len(all_suspicious),
        'categories': {
            'secrets_access': len(secrets),
            'kubectl_exec': len(exec_events),
            'privileged_pods': len(privileged),
            'rbac_escalation': len(rbac),
            'system_pod_access': len(system_access),
            'suspicious_pod_names': len(suspicious_pods)
        },
        'suspicious_events': all_suspicious
    }

    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Результат сохранен в {output_file}")

    # Выводим краткую сводку
    print("\n" + "="*60)
    print("КРАТКАЯ СВОДКА ПОДОЗРИТЕЛЬНЫХ СОБЫТИЙ")
    print("="*60)

    for item in all_suspicious:
        summary = item['summary']
        event_type = item['type']
        print(f"\n[{event_type.upper()}]")
        print(f"  Время: {summary.get('timestamp')}")
        print(f"  Пользователь: {summary.get('user')}")

        if event_type == 'secrets_access':
            print(f"  Namespace: {summary.get('namespace')}")
            print(f"  Действие: {summary.get('verb')}")
        elif event_type == 'kubectl_exec':
            print(f"  Pod: {summary.get('namespace')}/{summary.get('pod_name')}")
        elif event_type == 'privileged_pod':
            print(f"  Pod: {summary.get('namespace')}/{summary.get('pod_name')}")
            print(f"  Image: {summary.get('image')}")
        elif event_type == 'rbac_escalation':
            print(f"  Binding: {summary.get('binding_name')}")
            print(f"  Role: {summary.get('role')}")
            print(f"  Subjects: {summary.get('subjects')}")
        elif event_type == 'system_pod_access':
            print(f"  Pod: {summary.get('pod_name')}")
            print(f"  Access type: {summary.get('access_type')}")
        elif event_type == 'suspicious_pod_name':
            print(f"  Pod: {summary.get('namespace')}/{summary.get('pod_name')}")


if __name__ == '__main__':
    main()
