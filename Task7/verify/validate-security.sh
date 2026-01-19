#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[1/4] Check PodSecurity labels on namespace audit-zone"
kubectl get ns audit-zone -o jsonpath='{.metadata.labels.pod-security\.kubernetes\.io/enforce}{"\n"}' | grep -qx "restricted"

echo "[2/4] Check Gatekeeper is reachable (optional)"
if kubectl get pods -n gatekeeper-system >/dev/null 2>&1; then
  kubectl get pods -n gatekeeper-system
else
  echo "  gatekeeper-system namespace not found (skip)."
fi

echo "[3/4] Server-side validate secure manifests (should PASS)"
kubectl apply --dry-run=server -f "${ROOT_DIR}/secure-manifests/" >/dev/null

echo "[4/4] Server-side validate insecure manifests (should FAIL overall)"
if kubectl apply --dry-run=server -f "${ROOT_DIR}/insecure-manifests/" >/dev/null 2>&1; then
  echo "ERROR: insecure manifests unexpectedly passed validation" >&2
  exit 1
else
  echo "ok: insecure manifests rejected"
fi

echo "DONE"

