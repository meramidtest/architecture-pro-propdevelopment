minikube stop


mkdir -p ~/.minikube/files/etc/ssl/certs

cat <<EOF > ~/.minikube/files/etc/ssl/certs/audit-policy.yaml
# Audit policy to log all CRUD operations on resources
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # Log all CRUD operations at RequestResponse level for detailed auditing
  - level: RequestResponse
    verbs: ["create", "get", "list", "watch", "update", "patch", "delete", "deletecollection"]
    resources:
      - group: ""
        resources: ["*"]
      - group: "apps"
        resources: ["*"]
      - group: "batch"
        resources: ["*"]
      - group: "networking.k8s.io"
        resources: ["*"]
      - group: "rbac.authorization.k8s.io"
        resources: ["*"]
  # Fallback: log other requests at Metadata level
  - level: Metadata
EOF

minikube start \
  --extra-config=apiserver.audit-policy-file=/etc/ssl/certs/audit-policy.yaml \
  --extra-config=apiserver.audit-log-path=-

kubectl logs kube-apiserver-minikube -n kube-system | grep audit.k8s.io/v1