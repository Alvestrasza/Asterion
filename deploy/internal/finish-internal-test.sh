#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SOURCE_DIR=$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)

echo "This finishes one internal Asterion node after the dedicated database and roles exist."
echo "The migration URL is used once and is not stored. The runtime URL is stored root-only by the installer."
"${SCRIPT_DIR}/migrate-internal.sh"
sudo /bin/bash "${SOURCE_DIR}/install-staged-release.sh" internal-test
