#!/usr/bin/env bash
set -Eeuo pipefail

SOURCE_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
ACTION=${1:-}

case "${ACTION}" in
  check)
    if [[ ${EUID} -ne 0 ]]; then
      echo "The staged installer check must run through the approved sudo rule." >&2
      exit 1
    fi
    test -f "${SOURCE_DIR}/artifact/server.js"
    bash -n "${SOURCE_DIR}/deploy/internal/install-internal-test.sh"
    echo "Asterion staged installer dispatch is ready."
    ;;
  internal-test)
    shift
    exec /bin/bash "${SOURCE_DIR}/deploy/internal/install-internal-test.sh" "$@"
    ;;
  *)
    echo "Usage: $0 {check|internal-test}" >&2
    exit 2
    ;;
esac
