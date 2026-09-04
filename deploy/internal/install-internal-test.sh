#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this installer with sudo." >&2
  exit 1
fi

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SOURCE_DIR=$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)
ARTIFACT_DIR="${SOURCE_DIR}/artifact"
RELEASE_ID=${ASTERION_RELEASE_ID:-$(basename -- "${SOURCE_DIR}")}
SITE_ROOT=/opt/sites/asterion-internal
RELEASE_DIR="${SITE_ROOT}/releases/${RELEASE_ID}"
CURRENT_LINK="${SITE_ROOT}/current"
ENV_DIR=/etc/asterion-internal
ENV_FILE="${ENV_DIR}/asterion.env"
SERVICE_FILE=/etc/systemd/system/asterion-internal.service
NGINX_FILE=/etc/nginx/sites-available/asterion-internal.conf
NGINX_LINK=/etc/nginx/sites-enabled/asterion-internal.conf

case "${SOURCE_DIR}" in
  /home/*/releases/asterion-*) ;;
  *) echo "Refusing source outside /home/<user>/releases/asterion-*." >&2; exit 1 ;;
esac

if [[ ! -f "${ARTIFACT_DIR}/server.js" || ! -f "${SOURCE_DIR}/deploy/internal/asterion-internal.service" ]]; then
  echo "The staged release is incomplete." >&2
  exit 1
fi

if ! id webapps >/dev/null 2>&1; then
  echo "Required service account 'webapps' does not exist." >&2
  exit 1
fi

install -d -m 0755 -o root -g root "${SITE_ROOT}/releases"
install -d -m 0750 -o root -g www-data "${ENV_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  read -r -s -p "Asterion runtime DATABASE_URL: " DATABASE_URL
  echo
  if [[ ${DATABASE_URL} != postgresql://* && ${DATABASE_URL} != postgres://* ]]; then
    echo "DATABASE_URL must be a PostgreSQL URL." >&2
    exit 1
  fi

  AUTH_SECRET=$(openssl rand -base64 48 | tr -d '\n')
  umask 0027
  {
    printf 'NODE_ENV=production\n'
    printf 'HOSTNAME=127.0.0.1\n'
    printf 'PORT=3011\n'
    printf 'DATABASE_URL=%s\n' "${DATABASE_URL}"
    printf 'AUTH_SECRET=%s\n' "${AUTH_SECRET}"
    printf 'AUTH_TRUST_HOST=true\n'
    printf 'ASTERION_INTERNAL_TEST_MODE=true\n'
  } > "${ENV_FILE}"
  chown root:www-data "${ENV_FILE}"
  chmod 0640 "${ENV_FILE}"
  unset DATABASE_URL AUTH_SECRET
else
  if ! grep -qx 'ASTERION_INTERNAL_TEST_MODE=true' "${ENV_FILE}"; then
    echo "Existing environment file does not explicitly enable internal test mode." >&2
    exit 1
  fi
  chown root:www-data "${ENV_FILE}"
  chmod 0640 "${ENV_FILE}"
fi

if [[ -e "${RELEASE_DIR}" ]]; then
  echo "Release already exists: ${RELEASE_DIR}" >&2
  exit 1
fi

PREVIOUS_TARGET=""
if [[ -L "${CURRENT_LINK}" ]]; then
  PREVIOUS_TARGET=$(readlink -f -- "${CURRENT_LINK}" || true)
fi

rollback() {
  local exit_code=$?
  trap - ERR
  if [[ -n "${PREVIOUS_TARGET}" && -d "${PREVIOUS_TARGET}" ]]; then
    ln -sfn -- "${PREVIOUS_TARGET}" "${CURRENT_LINK}.rollback"
    mv -Tf -- "${CURRENT_LINK}.rollback" "${CURRENT_LINK}"
    systemctl restart asterion-internal.service || true
  elif [[ -L "${CURRENT_LINK}" ]]; then
    rm -f -- "${CURRENT_LINK}"
  fi
  echo "Installation failed; the previous application target was restored when available." >&2
  exit "${exit_code}"
}
trap rollback ERR

install -d -m 0755 -o webapps -g www-data "${RELEASE_DIR}"
cp -a -- "${ARTIFACT_DIR}/." "${RELEASE_DIR}/"
chown -R webapps:www-data "${RELEASE_DIR}"
find "${RELEASE_DIR}" -type d -exec chmod 0755 {} +
find "${RELEASE_DIR}" -type f -exec chmod 0644 {} +
install -d -m 0755 -o webapps -g www-data "${RELEASE_DIR}/.next/cache"

install -m 0644 -o root -g root "${SOURCE_DIR}/deploy/internal/asterion-internal.service" "${SERVICE_FILE}"
install -m 0644 -o root -g root "${SOURCE_DIR}/deploy/internal/asterion-internal.nginx.conf" "${NGINX_FILE}"
ln -sfn -- "${NGINX_FILE}" "${NGINX_LINK}"

ln -sfn -- "${RELEASE_DIR}" "${CURRENT_LINK}.next"
mv -Tf -- "${CURRENT_LINK}.next" "${CURRENT_LINK}"

systemctl daemon-reload
nginx -t
systemctl enable asterion-internal.service
systemctl restart asterion-internal.service

for _ in {1..20}; do
  if curl --fail --silent --show-error http://127.0.0.1:3011/api/health >/dev/null; then
    break
  fi
  sleep 1
done
curl --fail --silent --show-error http://127.0.0.1:3011/api/health >/dev/null

systemctl reload nginx
curl --fail --silent --show-error http://127.0.0.1:8088/api/health >/dev/null

trap - ERR
echo "Asterion internal test service is active on the internal Nginx listener (port 8088)."
