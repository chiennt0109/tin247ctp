#!/usr/bin/env bash
set -euo pipefail

# Install at nginx's `http` scope so the limit is effective even when the
# production server-block filename is unknown. The finite 260 MiB ceiling is
# intentionally safer than disabling client_max_body_size.
SOURCE_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/problem-test-upload.conf"
TARGET_FILE="/etc/nginx/conf.d/tin247ctp-problem-test-upload.conf"

if [[ ${EUID} -ne 0 ]]; then
    echo "ERROR: Run this script with sudo." >&2
    exit 1
fi

if ! command -v nginx >/dev/null 2>&1; then
    echo "ERROR: nginx was not found." >&2
    exit 1
fi

if [[ ! -f "${SOURCE_FILE}" ]]; then
    echo "ERROR: Missing ${SOURCE_FILE}. Pull the latest repository first." >&2
    exit 1
fi

backup=""
if [[ -f "${TARGET_FILE}" ]]; then
    backup="$(mktemp)"
    cp "${TARGET_FILE}" "${backup}"
fi

install -m 0644 "${SOURCE_FILE}" "${TARGET_FILE}"

if ! nginx -t; then
    if [[ -n "${backup}" ]]; then
        cp "${backup}" "${TARGET_FILE}"
    else
        rm -f "${TARGET_FILE}"
    fi
    echo "ERROR: Invalid nginx configuration; the previous state was restored." >&2
    exit 1
fi

systemctl reload nginx

if ! nginx -T 2>&1 | grep -Fq -- "client_max_body_size 260m;"; then
    echo "ERROR: nginx reloaded but the 260 MiB limit is not active." >&2
    exit 1
fi

rm -f "${backup}"
echo "OK: nginx now accepts requests up to 260 MiB."
echo "No Django service restart is required to fix nginx HTTP 413."
