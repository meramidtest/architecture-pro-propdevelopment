#!/usr/bin/env bash
set -euo pipefail

kubectl apply -f role-bindings/role-bindings-cluster-platform-admin.yaml
kubectl apply -f role-bindings/role-binding-ns-auth-deployer.yaml
kubectl apply -f role-bindings/role-binding-ns-data-deployer.yaml
kubectl apply -f role-bindings/role-binding-ns-client-mart-deployer.yaml
kubectl apply -f role-bindings/role-binding-ns-client-mart-qa.yaml

