#!/usr/bin/env bash
set -euo pipefail

./create-namespaces.sh

kubectl apply -f roles/role-cluster-platform-admin.yaml
kubectl apply -f roles/role-ns-auth-deployer.yaml
kubectl apply -f roles/role-ns-data-deployer.yaml
kubectl apply -f roles/role-ns-client-mart-deployer.yaml
kubectl apply -f roles/role-ns-client-mart-qa.yaml
