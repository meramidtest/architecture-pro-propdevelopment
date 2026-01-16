#!/usr/bin/env bash
set -euo pipefail

kubectl apply -f namespaces/namespace-systems-auth.yaml
kubectl apply -f namespaces/namespace-systems-data.yaml
kubectl apply -f namespaces/namespace-systems-client-mart.yaml

