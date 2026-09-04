#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
DATABASE_NAME=asterion_internal
OWNER_ROLE=asterion_internal_owner
APP_ROLE=asterion_internal_app

read -r -p "PostgreSQL cluster-admin connection URL (without a password): " ADMIN_URL
echo
if [[ ${ADMIN_URL} != postgresql://* && ${ADMIN_URL} != postgres://* ]]; then
  echo "The administrator connection must be a PostgreSQL URL." >&2
  exit 1
fi

AUTHORITY=${ADMIN_URL#*://}
CREDENTIALS=${AUTHORITY%%@*}
if [[ ${AUTHORITY} == *@* && ${CREDENTIALS} == *:* ]]; then
  echo "Do not embed the administrator password in the URL; psql will request it securely." >&2
  exit 1
fi

psql "${ADMIN_URL}" \
  --set=ON_ERROR_STOP=1 \
  --set="database_name=${DATABASE_NAME}" \
  --set="owner_role=${OWNER_ROLE}" \
  --set="app_role=${APP_ROLE}" \
  --file="${SOURCE_DIR}/deploy/postgresql/bootstrap.sql"

echo "Set the migration-role password:"
psql "${ADMIN_URL}" --set=ON_ERROR_STOP=1 --command="\\password ${OWNER_ROLE}"
echo "Set the runtime-role password:"
psql "${ADMIN_URL}" --set=ON_ERROR_STOP=1 --command="\\password ${APP_ROLE}"
unset ADMIN_URL

echo "Database '${DATABASE_NAME}' and its two roles are provisioned."
echo "Use the owner role once for migrations and the app role in the protected service environment."
