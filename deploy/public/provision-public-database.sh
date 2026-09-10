#!/usr/bin/env bash
set -Eeuo pipefail

# Explicit first provisioning on the local PostgreSQL leader only. No remote
# connection URL, inherited connection target, existing-object reuse, or drop.
if [[ $# -ne 3 ]]; then
  echo "Usage: sudo -u postgres bash provision-public-database.sh <new-database> <new-owner-role> <new-runtime-role>" >&2
  exit 1
fi
DATABASE_NAME=$1
OWNER_ROLE=$2
RUNTIME_ROLE=$3
for identifier in "${DATABASE_NAME}" "${OWNER_ROLE}" "${RUNTIME_ROLE}"; do
  if [[ ! ${identifier} =~ ^[a-z][a-z0-9_]{0,62}$ || ${identifier} == pg_* ||
        ${identifier} == postgres || ${identifier} == template* ||
        ${identifier} =~ (^|_)(internal|test|testing|dev|development)(_|$) ]]; then
    echo "Use new public identifiers: lowercase letters, digits, underscores, maximum 63 characters; system and internal/test/dev names are refused." >&2
    exit 1
  fi
done
[[ ${DATABASE_NAME} != "${OWNER_ROLE}" && ${DATABASE_NAME} != "${RUNTIME_ROLE}" && ${OWNER_ROLE} != "${RUNTIME_ROLE}" ]] || {
  echo "Database, owner role, and runtime role must use distinct new names." >&2; exit 1;
}
[[ $(id -un) == postgres ]] || {
  echo "Run as the PostgreSQL operating-system account on the current database leader, using sudo -u postgres." >&2; exit 1;
}
[[ -t 0 && -t 1 ]] || { echo "An interactive terminal is required for the two password prompts." >&2; exit 1; }
command -v psql >/dev/null || { echo "The PostgreSQL client is required on the database node." >&2; exit 1; }
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ -r ${SCRIPT_DIR}/public-database.sql ]] || { echo "The matching public-database.sql file is missing." >&2; exit 1; }

# Refuse ambient libpq routing/credentials and a personal psql startup file.
# The profile is intentionally fixed to the reviewed standard local socket/port.
unset PGHOST PGHOSTADDR PGPORT PGDATABASE PGUSER PGPASSWORD PGSERVICE PGSERVICEFILE PGOPTIONS PGTARGETSESSIONATTRS
export PGCONNECT_TIMEOUT=5

echo "Preparing the three explicitly selected new public database objects on the local leader."
echo "No existing object is reused. Passwords are prompted by psql, never supplied inline."
if ! psql -X --no-password --host=/var/run/postgresql --port=5432 \
    --username=postgres --dbname=postgres --set=ON_ERROR_STOP=1 --set=VERBOSITY=terse \
    --set="database_name=${DATABASE_NAME}" --set="owner_role=${OWNER_ROLE}" --set="runtime_role=${RUNTIME_ROLE}" \
    --file="${SCRIPT_DIR}/public-database.sql"; then
  echo "Provisioning stopped. Inspect the selected objects privately before any retry; no automatic resume or deletion is performed." >&2
  echo "A committed role or database may remain after a later phase fails. Do not rerun against existing objects or weaken the guards." >&2
  exit 1
fi
echo "Public database roles and privileges were prepared. HBA rules, transport protection, application migrations, and web-node connections still need acceptance."
