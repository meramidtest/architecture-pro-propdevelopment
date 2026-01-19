
### Что сделано

- создан namespace audit-zone с PodSecurity Admission уровнем restricted (через labels в 01-create-namespace.yaml).
- В insecure-manifests/ лежат 3 манифеста pod, которые должны быть заблокированы:
    - 01-privileged-pod.yaml - privileged=true
    - 02-hostpath-pod.yaml - используется hostPath
    - 03-root-user-pod.yaml - запуск от root (runAsUser: 0)
- В secure-manifests/ лежат 3 нормальных pod-манифеста (busybox + sleep), которые проходят restricted и Gatekeeper.

### gatekeeper политики

Добавлены правила:
- запрет privileged=true
- запрет hostPath
- требование runAsNonRoot=true
- требование readOnlyRootFilesystem=true

Файлы лежа тут:
- gatekeeper/constraint-templates/ - шаблоны
- gatekeeper/constraints - сами ограничения

### Аудит

audit-policy.yaml - пример audit policy для kube-apiserver:
- для pod в audit-zone включен полный лог (RequestResponse)
- для остального пишутся только метаданные

### Как проверить

Проверка идет через kubectl apply --dry-run=server, поэтому admission срабатывает, но поды реально не создаются.

Убедиться что установлен gatekeeper - `kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.14.0/deploy/gatekeeper.yaml `

```bash
cd Task7

chmod +x verify/*.sh

./verify/verify-admission.sh
./verify/validate-security.sh
