# ---- Функция для создания пользователей в k8s
create_k8s_user_cert() {
  local username="$1"
  local team="$2"

  local key_file="${username}.key"
  local csr_file="${username}.csr"
  local crt_file="${username}.crt"
  local k8s_csr_name="${username}-csr"

  echo "> creating user cert for CN=${username}, O=${team}"
  echo "  files: ${key_file}, ${csr_file}, ${crt_file}"
  echo "  k8s csr: ${k8s_csr_name}"

  # 1) Generate private key + CSR
  openssl req -new \
    -newkey rsa:2048 \
    -nodes \
    -keyout "${key_file}" \
    -out "${csr_file}" \
    -subj "/CN=${username}/O=${team}"

  # 2) (Re)create the Kubernetes CSR object
  kubectl delete csr "${k8s_csr_name}" --ignore-not-found >/dev/null 2>&1 || true

  kubectl apply -f - <<EOF
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: ${k8s_csr_name}
spec:
  request: $(base64 < "${csr_file}" | tr -d '\n')
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 31536000
  usages:
  - client auth
EOF

  # 3) Approve CSR
  kubectl certificate approve "${k8s_csr_name}" >/dev/null

  # 4) Download signed cert
  kubectl get csr "${k8s_csr_name}" -o jsonpath='{.status.certificate}' \
    | base64 --decode > "${crt_file}"

  # 5) Add user credentials into kubeconfig
  kubectl config set-credentials "${username}" \
    --client-certificate="${crt_file}" \
    --client-key="${key_file}" \
    --embed-certs=true >/dev/null

  echo "!! user created: ${username}"
}

# администратор k8s
create_k8s_user_cert "user-k8s-admin-ivan-mihejev" "devops-team"

# разработчик витрины
create_k8s_user_cert "user-dev-mart-system-alisa-abramovich" "dev-team"

# разработчик core команды (авторизация и общее хранилище)
create_k8s_user_cert "user-dev-core-systems-kirill-malofeev" "dev-team"

# QA команды витрины
create_k8s_user_cert "user-qa-mart-system-andrey-nadolinsky" "qa-team"

