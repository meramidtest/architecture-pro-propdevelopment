# Отчет по результатам анализа Kubernetes Audit Log

Дата анализа: 2026-01-17  
Подозрительных событий: 10

## Подозрительные события

1. Доступ к секретам:
    - Кто: minikube-user (system:masters)
    - Где: kube-system
    - Что: list secrets
    - Почему подозрительно: просмотр секретов в kube-system может дать доступ к токенам и другим служебным данным

2. Привилегированные поды:
    - Кто: minikube-user
    - Где: secure-ops
    - Что: создан pod privileged-pod (alpine), privileged=true
    - Коментарий: privileged pod может получить доступ к хосту и использоваться для захвата ноды

3. Использование kubectl exec в чужом поде:
    - Кто: minikube-user
    - Где: kube-system, pod coredns-66bc5c9577-cbn92
    - Что делал: exec с командой cat /etc/resolv.conf
    - Почему подозрительно: exec в системные поды часто используют для разведки и дальнейших попыток атак

4. Создание RoleBinding с правами cluster-admin:
    - Кто: minikube-user
    - Где: secure-ops
    - Что: RoleBinding escalate-binding выдал права cluster-admin для ServiceAccount secure-ops:monitoring
    - К чему привело: service account получил максимальные права в namespace (что уже опасно)

5. Удаление audit-policy.yaml:
    - Кто: не найдено в логах
    - Возможные последствия: прямого удаления/изменения audit-policy я не увидел, но было несколько чтений логов kube-apiserver, что похоже на разведку

## Вывод

В логах просматривается типовая цепочка дейтсвий:
- разведка (просмотр секретов, exec в системные поды, чтение логов API-сервера)
- закрепление (создание подозрительных pod)
- повышение прав (RoleBinding с cluster-admin)

Что можно считать компрометацией кластера:
- доступ к секретам kube-system
- запуск privileged pod
- выдача cluster-admin прав сервисному аккаунту

Ошибки RBAC:
- пользователь minikube-user в группе system:masters имеет слишком широкие права
- возможна эскалация прав через RoleBinding (если это не ограничивать)
