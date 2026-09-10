#!/usr/bin/env bash
set -Eeuo pipefail

# Explicit owner-run first activation, after database/Keycloak preparation.
# Does not change DNS, load balancers, firewall rules, certificates or migrations.
if [[ ${EUID} -ne 0 || $# -ne 1 || ( $1 != --sync-worker && $1 != --web-only ) ]]; then
  echo "Usage: sudo bash deploy/public/activate-public.sh --sync-worker|--web-only" >&2
  exit 1
fi
WORKER_MODE=$1
ACTIVATION_PID=$BASHPID
ACTIVATION_STAGE=preflight
SITE_ROOT=/opt/sites/asterion-public
ENV_FILE=/etc/asterion-public/asterion.env
NGINX_FILE=/etc/nginx/sites-available/asterion-public.conf
NGINX_LINK=/etc/nginx/sites-enabled/asterion-public.conf
exec 9>/run/lock/asterion-public-activation.lock
flock -n 9 || { echo "Another public preparation or activation is running." >&2; exit 1; }
CURRENT_DIR=$(readlink -f -- "${SITE_ROOT}/current")
case "${CURRENT_DIR}" in
  /opt/sites/asterion-public/releases/asterion-*) ;;
  *) echo "The public release target is not valid." >&2; exit 1 ;;
esac
[[ -f ${ENV_FILE} && ! -L ${ENV_FILE} && $(stat -c '%u:%a' "${ENV_FILE}") == 0:600 ]] || {
  echo "Public environment must be a root-owned regular file with mode 0600." >&2; exit 1;
}
[[ ! -e ${NGINX_FILE} && ! -L ${NGINX_FILE} && ! -e ${NGINX_LINK} && ! -L ${NGINX_LINK} ]] || {
  echo "A public proxy site already exists; first activation will not overwrite it." >&2; exit 1;
}
if systemctl is-active --quiet asterion-public.service || systemctl is-active --quiet asterion-public-access-sync.timer; then
  echo "A public service is already active; use the reviewed release procedure." >&2
  exit 1
fi
TEMP_CONFIG=$(mktemp /run/asterion-public-nginx.XXXXXX)
trap 'if [[ ${BASHPID} == "${ACTIVATION_PID}" ]]; then rm -f -- "${TEMP_CONFIG}"; fi' EXIT
run_preflight() {
  systemd-run --quiet --pipe --wait --collect \
    --property="EnvironmentFile=${ENV_FILE}" \
    --property=User=webapps --property=Group=www-data \
    /usr/bin/node "${CURRENT_DIR}/.asterion-operations/public-config.mjs" "$1"
}
run_preflight --render-nginx > "${TEMP_CONFIG}"
CANONICAL_HOST=$(run_preflight --canonical-host)
ALTERNATE_HOST=$(run_preflight --alternate-host)
TLS_SERVER_NAME=$(run_preflight --backend-tls-server-name)
TLS_CA_FILE=$(run_preflight --backend-tls-ca-file)
[[ -f ${TLS_CA_FILE} && -r ${TLS_CA_FILE} ]] || {
  echo "The reviewed backend certificate trust bundle is unavailable." >&2; exit 1;
}
# The certificate identity can be the internal backend name while HTTP Host
# selects the public virtual host. Never disable certificate verification.
backend_request() {
  curl -4 --noproxy '*' --silent --show-error --max-time 5 \
    --cacert "${TLS_CA_FILE}" --resolve "${TLS_SERVER_NAME}:443:127.0.0.1" "$@"
}
healthy_response() {
  /usr/bin/node -e 'let body="";process.stdin.setEncoding("utf8");process.stdin.on("data",c=>body+=c);process.stdin.on("end",()=>{try{const value=JSON.parse(body);if(value.status!=="healthy"||value.database!=="reachable")process.exit(1)}catch{process.exit(1)}})'
}

probe_readiness() {
  local response status result
  if response=$("$@" --max-filesize 65536 --write-out $'\n%{http_code}'); then
    status=${response##*$'\n'}
    if [[ ${status} != 200 ]]; then
      READINESS_DETAIL="unexpected_http_status"
      [[ ${status} =~ ^[0-9]{3}$ ]] && READINESS_DETAIL="HTTP_${status}"
      return 1
    fi
    # Never follow redirects or accept a generic HTTP 200 from another vhost.
    # Keep response bodies out of diagnostic output.
    if printf '%s' "${response%$'\n'*}" | healthy_response; then return 0; fi
    READINESS_DETAIL=invalid_health_response
  else
    result=$?
    READINESS_DETAIL="curl_exit_${result}"
  fi
  return 1
}

wait_for_readiness() {
  local label=$1 attempt
  shift
  for attempt in {1..20}; do
    if probe_readiness "$@"; then
      echo "${label} readiness passed."
      return 0
    fi
    echo "${label} readiness pending (${attempt}/20): ${READINESS_DETAIL}." >&2
    if [[ ${attempt} -lt 20 ]]; then sleep 1; fi
  done
  echo "${label} readiness failed: ${READINESS_DETAIL}." >&2
  return 1
}

rollback() {
  local result=$?
  trap - ERR
  # ERR is inherited by functions, pipelines and command substitutions. Only
  # the main shell may stop services or remove proxy files.
  if [[ ${BASHPID} != "${ACTIVATION_PID}" ]]; then exit "${result}"; fi
  echo "Public activation failed at ${ACTIVATION_STAGE} (exit ${result})." >&2
  systemctl disable --now asterion-public-access-sync.timer >/dev/null 2>&1 || true
  systemctl stop asterion-public-access-sync.service >/dev/null 2>&1 || true
  systemctl disable --now asterion-public.service >/dev/null 2>&1 || true
  # These exact files did not exist before this first activation.
  rm -f -- "${NGINX_LINK}" "${NGINX_FILE}"
  if nginx -t; then systemctl reload nginx || true; fi
  echo "Public activation failed and was deactivated. Release, environment, database, and internal test service were retained." >&2
  exit "${result}"
}
trap rollback ERR
ACTIVATION_STAGE=install-proxy
install -m 0644 -o root -g root "${TEMP_CONFIG}" "${NGINX_FILE}"
ln -s -- "${NGINX_FILE}" "${NGINX_LINK}"
nginx -t
ACTIVATION_STAGE=start-service
systemctl start asterion-public.service
ACTIVATION_STAGE=local-readiness
wait_for_readiness Local curl -4 --noproxy '*' --silent --show-error --max-time 2 http://127.0.0.1:3012/api/health
ACTIVATION_STAGE=reload-nginx
systemctl reload nginx
ACTIVATION_STAGE=https-readiness
# A reload acknowledges the signal before the new workers necessarily serve
# requests. Poll the exact verified HTTPS response, not only the reload exit.
wait_for_readiness HTTPS backend_request -H "Host: ${CANONICAL_HOST}" \
  "https://${TLS_SERVER_NAME}/api/health"
ACTIVATION_STAGE=alternate-redirect
REDIRECT_RESULT=$(backend_request --output /dev/null --write-out '%{http_code} %{redirect_url}' \
  -H "Host: ${ALTERNATE_HOST}" "https://${TLS_SERVER_NAME}/api/health")
[[ ${REDIRECT_RESULT} == "308 https://${CANONICAL_HOST}/api/health" ]] || {
  echo "The alternate origin did not return the exact canonical redirect." >&2; false;
}
ACTIVATION_STAGE=private-route
PRIVATE_STATUS=$(backend_request --output /dev/null --write-out '%{http_code}' \
  -H "Host: ${CANONICAL_HOST}" "https://${TLS_SERVER_NAME}/api/internal/access-sync")
[[ ${PRIVATE_STATUS} == 404 ]] || {
  echo "The public proxy did not deny the private synchronization endpoint." >&2; false;
}
if [[ ${WORKER_MODE} == --sync-worker ]]; then
  ACTIVATION_STAGE=start-sync-worker
  systemctl start asterion-public-access-sync.service
  systemctl enable --now asterion-public-access-sync.timer
fi
ACTIVATION_STAGE=enable-service
systemctl enable asterion-public.service
trap - ERR
echo "Public backend readiness passed. Keep the external route closed until real login, permissions, and two-user acceptance pass."
echo "The internal test profile was not changed. No migration or identity infrastructure change was performed."
