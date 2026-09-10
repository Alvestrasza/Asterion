#!/usr/bin/env bash
set -Eeuo pipefail

# Refresh only an installed, never-activated candidate. Keep the previous release
# and protected environment. No migration, listener, service start or TLS change.
if [[ ${EUID} -ne 0 || $# -ne 3 ]]; then
  echo "Usage: sudo bash deploy/public/refresh-prepared-public.sh <expected-current-id> <new-release-id> <absolute-linux-artifact-directory>" >&2
  exit 1
fi
EXPECTED_ID=$1
RELEASE_ID=$2
for identifier in "${EXPECTED_ID}" "${RELEASE_ID}"; do
  [[ ${identifier} =~ ^asterion-[A-Za-z0-9][A-Za-z0-9._-]{0,95}$ ]] || {
    echo "Invalid immutable release id." >&2; exit 1;
  }
done
[[ ${EXPECTED_ID} != "${RELEASE_ID}" ]] || { echo "A new immutable release id is required." >&2; exit 1; }
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
ARTIFACT_DIR=$(realpath -e -- "$3")
SITE_ROOT=/opt/sites/asterion-public
ENV_DIR=/etc/asterion-public
ENV_FILE=${ENV_DIR}/asterion.env
RELEASE_DIR=${SITE_ROOT}/releases/${RELEASE_ID}
EXPECTED_DIR=${SITE_ROOT}/releases/${EXPECTED_ID}
for target in "${SITE_ROOT}" "${SITE_ROOT}/releases" "${ENV_DIR}"; do
  [[ $(realpath -e -- "${target}") == "${target}" && $(stat -c '%u' "${target}") == 0 ]] || {
    echo "An installation root is missing, symlinked, or not root-owned." >&2; exit 1;
  }
done
exec 9>/run/lock/asterion-public-activation.lock
flock -n 9 || { echo "Another public preparation or activation is running." >&2; exit 1; }
[[ -L ${SITE_ROOT}/current && $(readlink -f -- "${SITE_ROOT}/current") == "${EXPECTED_DIR}" &&
   $(realpath -e -- "${EXPECTED_DIR}") == "${EXPECTED_DIR}" &&
   ! -e ${RELEASE_DIR} && ! -L ${RELEASE_DIR} ]] || {
  echo "The current release differs from the reviewed target or the new release already exists." >&2; exit 1;
}
[[ -f ${ENV_FILE} && ! -L ${ENV_FILE} && $(stat -c '%u:%a' "${ENV_FILE}") == 0:600 ]] || {
  echo "The existing protected environment must be root-owned with mode 0600." >&2; exit 1;
}
for target in /etc/nginx/sites-available/asterion-public.conf /etc/nginx/sites-enabled/asterion-public.conf; do
  [[ ! -e ${target} && ! -L ${target} ]] || {
    echo "A public proxy already exists; use an active-release procedure instead." >&2; exit 1;
  }
done
for unit in asterion-public.service asterion-public-access-sync.service asterion-public-access-sync.timer; do
  state=$(systemctl show "${unit}" --property=ActiveState --value)
  enabled=$(systemctl show "${unit}" --property=UnitFileState --value)
  [[ $(systemctl show "${unit}" --property=LoadState --value) == loaded &&
     ${state} == inactive && ( ${enabled} == disabled || ${enabled} == static ) ]] || {
    echo "All public units must already be installed, inactive and disabled/static." >&2; exit 1;
  }
  # A script-only refresh must never replace changed unit contracts silently.
  cmp -s -- "${SCRIPT_DIR}/${unit}" "/etc/systemd/system/${unit}" || {
    echo "Installed public units differ from this candidate; review their upgrade separately." >&2; exit 1;
  }
done
case "${ARTIFACT_DIR}" in
  /home/*/releases/asterion-*/artifact | /home/*/releases/asterion-*/.next/standalone) ;;
  *) echo "Artifact must belong to a reviewed Linux staging release." >&2; exit 1 ;;
esac
[[ -f ${ARTIFACT_DIR}/server.js && -f ${ARTIFACT_DIR}/start-asterion.mjs &&
   -f ${ARTIFACT_DIR}/.asterion-operations/public-config.mjs &&
   -d ${ARTIFACT_DIR}/.next/static && -d ${ARTIFACT_DIR}/public ]] || {
  echo "The guarded standalone artifact is incomplete." >&2; exit 1;
}
cmp -s -- "${SCRIPT_DIR}/public-config.mjs" "${ARTIFACT_DIR}/.asterion-operations/public-config.mjs" || {
  echo "The embedded guard differs from the reviewed source; rebuild one consistent artifact." >&2; exit 1;
}
cmp -s -- "${SCRIPT_DIR}/../../scripts/start-standalone.mjs" "${ARTIFACT_DIR}/start-asterion.mjs" || {
  echo "The standalone entry point differs from the reviewed source." >&2; exit 1;
}
while IFS= read -r -d '' link; do
  [[ $(readlink -- "${link}") != /* ]] || {
    echo "The artifact contains an absolute symlink; only relocatable links are permitted." >&2; exit 1;
  }
  resolved=$(realpath -e -- "${link}")
  [[ ${resolved} == "${ARTIFACT_DIR}/"* ]] || {
    echo "The artifact contains a symlink outside its own tree." >&2; exit 1;
  }
done < <(find "${ARTIFACT_DIR}" -type l -print0)
id webapps >/dev/null
getent group www-data >/dev/null

# Failures before the final atomic symlink switch leave current unchanged.
# Retain incomplete new directories for inspection rather than deleting evidence.
install -d -m 0755 -o root -g root "${RELEASE_DIR}"
cp -a -- "${ARTIFACT_DIR}/." "${RELEASE_DIR}/"
while IFS= read -r -d '' link; do
  [[ $(readlink -- "${link}") != /* && $(realpath -e -- "${link}") == "${RELEASE_DIR}/"* ]] || {
    echo "The copied artifact contains a link outside the immutable release; current was not changed." >&2; exit 1;
  }
done < <(find "${RELEASE_DIR}" -type l -print0)
chown -R root:root "${RELEASE_DIR}"
find "${RELEASE_DIR}" -type d -exec chmod 0755 {} +
find "${RELEASE_DIR}" -type f -exec chmod 0644 {} +
install -m 0644 -o root -g root "${SCRIPT_DIR}/run-access-sync.mjs" "${RELEASE_DIR}/.asterion-operations/"
install -d -m 0750 -o webapps -g www-data "${RELEASE_DIR}/.next/cache"
cmp -s -- "${SCRIPT_DIR}/public-config.mjs" "${RELEASE_DIR}/.asterion-operations/public-config.mjs"
NEXT_LINK=${SITE_ROOT}/.prepared-${RELEASE_ID}
[[ ! -e ${NEXT_LINK} && ! -L ${NEXT_LINK} ]] || {
  echo "The temporary release link already exists; inspect it before retrying." >&2; exit 1;
}
ln -s -- "${RELEASE_DIR}" "${NEXT_LINK}"
mv -Tf -- "${NEXT_LINK}" "${SITE_ROOT}/current"
echo "The stopped public candidate was refreshed. Previous release and protected environment were retained."
echo "No service was started, no listener installed, and no database or certificate changed."
