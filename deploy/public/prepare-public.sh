#!/usr/bin/env bash
set -Eeuo pipefail

# First provisioning only. This script neither starts a service nor enables a
# listener, runs migrations, opens a firewall, or changes the internal profile.
if [[ ${EUID} -ne 0 || $# -ne 2 ]]; then
  echo "Usage: sudo bash deploy/public/prepare-public.sh <release-id> <absolute-linux-artifact-directory>" >&2
  exit 1
fi
RELEASE_ID=$1
[[ ${RELEASE_ID} =~ ^asterion-[A-Za-z0-9][A-Za-z0-9._-]{0,95}$ ]] || {
  echo "Invalid immutable release id." >&2; exit 1;
}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
ARTIFACT_DIR=$(realpath -e -- "$2")
SITE_ROOT=/opt/sites/asterion-public
ENV_DIR=/etc/asterion-public
ENV_FILE=${ENV_DIR}/asterion.env
RELEASE_DIR=${SITE_ROOT}/releases/${RELEASE_ID}

for target in "${SITE_ROOT}" "${ENV_DIR}"; do
  [[ $(realpath -m -- "${target}") == "${target}" ]] || {
    echo "Refusing a symlinked installation root." >&2; exit 1;
  }
done
case "${ARTIFACT_DIR}" in
  /home/*/releases/asterion-*/artifact | /home/*/releases/asterion-*/.next/standalone) ;;
  *) echo "Artifact must be a reviewed Linux release under /home/<operator>/releases/asterion-*." >&2; exit 1 ;;
esac
[[ -f ${ARTIFACT_DIR}/server.js && -f ${ARTIFACT_DIR}/start-asterion.mjs &&
   -f ${ARTIFACT_DIR}/.asterion-operations/public-config.mjs &&
   -d ${ARTIFACT_DIR}/.next/static && -d ${ARTIFACT_DIR}/public ]] || {
  echo "The standalone Linux artifact is incomplete." >&2; exit 1;
}
cmp -s -- "${SCRIPT_DIR}/public-config.mjs" "${ARTIFACT_DIR}/.asterion-operations/public-config.mjs" || {
  echo "The public preflight does not match the reviewed artifact; rebuild from one consistent revision." >&2; exit 1;
}
while IFS= read -r -d '' link; do
  resolved=$(realpath -e -- "${link}")
  [[ ${resolved} == "${ARTIFACT_DIR}/"* ]] || {
    echo "Artifact contains a link outside its own tree." >&2; exit 1;
  }
done < <(find "${ARTIFACT_DIR}" -type l -print0)
id webapps >/dev/null 2>&1 || { echo "Required application service account is missing." >&2; exit 1; }
getent group www-data >/dev/null || { echo "Required application service group is missing." >&2; exit 1; }
for command_name in node systemctl systemd-run nginx curl flock cmp; do
  command -v "${command_name}" >/dev/null || { echo "A required runtime command is missing." >&2; exit 1; }
done
[[ -x /usr/bin/node ]] || { echo "This profile requires Node at /usr/bin/node." >&2; exit 1; }
/usr/bin/node -e 'if (Number(process.versions.node.split(".")[0]) < 22) process.exit(1)'
for unit in asterion-public.service asterion-public-access-sync.service asterion-public-access-sync.timer; do
  if systemctl cat "${unit}" >/dev/null 2>&1; then
    echo "Public units already exist; use the reviewed release procedure, not first provisioning." >&2
    exit 1
  fi
done
[[ ! -e ${SITE_ROOT}/current && ! -L ${SITE_ROOT}/current && ! -e ${RELEASE_DIR} ]] || {
  echo "Public installation already exists; nothing was overwritten." >&2; exit 1;
}
if [[ -e ${ENV_FILE} || -L ${ENV_FILE} ]]; then
  [[ -f ${ENV_FILE} && ! -L ${ENV_FILE} && $(stat -c '%u:%a' "${ENV_FILE}") == 0:600 ]] || {
    echo "Existing public environment must be a root-owned regular file with mode 0600." >&2; exit 1;
  }
fi

install -d -m 0755 -o root -g root "${SITE_ROOT}/releases"
install -d -m 0700 -o root -g root "${ENV_DIR}"
if [[ ! -e ${ENV_FILE} ]]; then
  install -m 0600 -o root -g root "${SCRIPT_DIR}/asterion-public.env.example" "${ENV_FILE}"
fi
install -d -m 0755 -o root -g root "${RELEASE_DIR}"
cp -a -- "${ARTIFACT_DIR}/." "${RELEASE_DIR}/"
chown -R root:root "${RELEASE_DIR}"
find "${RELEASE_DIR}" -type d -exec chmod 0755 {} +
find "${RELEASE_DIR}" -type f -exec chmod 0644 {} +
install -d -m 0755 -o root -g root "${RELEASE_DIR}/.asterion-operations"
install -m 0644 -o root -g root "${SCRIPT_DIR}/run-access-sync.mjs" "${RELEASE_DIR}/.asterion-operations/"
install -d -m 0750 -o webapps -g www-data "${RELEASE_DIR}/.next/cache"
ln -s -- "${RELEASE_DIR}" "${SITE_ROOT}/current"
for unit in asterion-public.service asterion-public-access-sync.service asterion-public-access-sync.timer; do
  install -m 0644 -o root -g root "${SCRIPT_DIR}/${unit}" "/etc/systemd/system/${unit}"
done
systemctl daemon-reload
echo "Public files prepared. All new units remain disabled and stopped. No public listener was installed."
echo "Review the protected environment, provision the separate database, and follow docs/PUBLIC-ACTIVATION.md."
