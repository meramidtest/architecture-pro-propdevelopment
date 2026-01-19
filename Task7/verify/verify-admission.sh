#!/usr/bin/env bash
set -euo pipefail

echo "[1/5] Create namespace (PodSecurity restricted)"
kubectl apply -f "./01-create-namespace.yaml"

echo "[2/5] Apply Gatekeeper templates + constraints"
kubectl apply -f "./gatekeeper/constraint-templates/"
kubectl apply -f "./gatekeeper/constraints/"

echo "[3/5] Validate: insecure manifests MUST be rejected (server-side dry-run)"
insecure=(
  "./insecure-manifests/01-privileged-pod.yaml"
  "./insecure-manifests/02-hostpath-pod.yaml"
  "./insecure-manifests/03-root-user-pod.yaml"
)

for f in "${insecure[@]}"; do
  echo "  - expecting REJECT: $(basename "$f")"
  if kubectl apply --dry-run=server -f "$f" >/dev/null 2>&1; then
    echo "ERROR: insecure manifest was ACCEPTED by admission: $f" >&2
    exit 1
  else
    echo "    ok (rejected)"
  fi
done

echo "[4/5] Validate: secure manifests MUST be accepted (server-side dry-run)"
secure=(
  "./secure-manifests/01-secure.yaml"
  "./secure-manifests/02-secure.yaml"
  "./secure-manifests/03-secure.yaml"
)

for f in "${secure[@]}"; do
  echo "  - expecting ACCEPT: $(basename "$f")"
  kubectl apply --dry-run=server -f "$f" >/dev/null
  echo "    ok (accepted)"
done

echo "[5/5] Show Gatekeeper constraint statuses (if Gatekeeper is installed)"
kubectl get constraints -A || true

echo "DONE"

