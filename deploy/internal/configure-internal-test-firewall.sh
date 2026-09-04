#!/usr/bin/env bash
set -Eeuo pipefail

ACTION=${1:-}
SOURCE_CIDR=${2:-}
PORT=8088
COMMENT="Asterion internal test"

if [[ ${EUID} -ne 0 ]]; then
  echo "Run this script with sudo." >&2
  exit 1
fi

if [[ ${ACTION} != "allow" && ${ACTION} != "remove" ]] || [[ -z ${SOURCE_CIDR} ]]; then
  echo "Usage: $0 {allow|remove} <trusted-private-cidr>" >&2
  exit 2
fi

python3 - "${SOURCE_CIDR}" <<'PY'
import ipaddress
import sys

try:
    network = ipaddress.ip_network(sys.argv[1], strict=False)
except ValueError as error:
    raise SystemExit(f"Invalid source CIDR: {error}")

if not network.is_private:
    raise SystemExit("The source CIDR must be a private IPv4 or IPv6 network.")
PY

if ! command -v ufw >/dev/null 2>&1; then
  echo "UFW is not installed." >&2
  exit 1
fi

if ! ufw status | grep -qx 'Status: active'; then
  echo "UFW is not active; refusing to change firewall state." >&2
  exit 1
fi

case "${ACTION}" in
  allow)
    ufw allow proto tcp from "${SOURCE_CIDR}" to any port "${PORT}" comment "${COMMENT}"
    ;;
  remove)
    ufw --force delete allow proto tcp from "${SOURCE_CIDR}" to any port "${PORT}"
    ;;
esac

ufw status numbered
