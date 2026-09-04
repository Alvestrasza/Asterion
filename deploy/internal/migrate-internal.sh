#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)

if [[ ! -x "${SOURCE_DIR}/node_modules/.bin/prisma" ]]; then
  echo "Install the staged release dependencies before running migrations." >&2
  exit 1
fi

read -r -s -p "Asterion migration DATABASE_URL: " DATABASE_URL
echo
if [[ ${DATABASE_URL} != postgresql://* && ${DATABASE_URL} != postgres://* ]]; then
  echo "DATABASE_URL must be a PostgreSQL URL." >&2
  exit 1
fi

export DATABASE_URL
"${SOURCE_DIR}/node_modules/.bin/prisma" migrate deploy
unset DATABASE_URL
echo "Asterion database migrations completed."
