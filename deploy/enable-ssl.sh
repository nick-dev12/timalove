#!/usr/bin/env bash
# =============================================================================
# TIMALOVE — Activer SSL après mise à jour DNS Cloudflare
# Usage (sur le VPS) :
#   sudo bash /home/jomas/timalove/deploy/enable-ssl.sh
# =============================================================================

set -euo pipefail

if [[ -f /etc/timalove/deploy.env ]]; then
    # shellcheck disable=SC1091
    source /etc/timalove/deploy.env
fi

DOMAIN="${DOMAIN:-mytimalove.com}"
SSL_EMAIL="${SSL_EMAIL:-admin@${DOMAIN}}"
DJANGO_DIR="${DJANGO_DIR:-/home/jomas/timalove/timalove}"
ENV_FILE="${DJANGO_DIR}/.env"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "Exécutez en root : sudo bash deploy/enable-ssl.sh" >&2
    exit 1
fi

echo "[enable-ssl] Certbot pour ${DOMAIN} + www.${DOMAIN}"
certbot --nginx \
    -d "$DOMAIN" -d "www.${DOMAIN}" \
    --non-interactive --agree-tos \
    -m "$SSL_EMAIL" \
    --redirect

if [[ -f "$ENV_FILE" ]]; then
    python3 - "$ENV_FILE" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
replacements = {
    "SECURE_SSL_REDIRECT": "True",
    "SECURE_HSTS_SECONDS": "31536000",
    "SESSION_COOKIE_SECURE": "True",
    "CSRF_COOKIE_SECURE": "True",
}
lines = []
seen = set()
for line in text.splitlines(True):
    key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
    if key in replacements:
        lines.append(f"{key}={replacements[key]}\n")
        seen.add(key)
    else:
        lines.append(line)
for key, val in replacements.items():
    if key not in seen:
        lines.append(f"{key}={val}\n")
path.write_text("".join(lines), encoding="utf-8")
PY
    systemctl restart daphne-timalove
    echo "[OK] SECURE_SSL_REDIRECT=True + Daphne redémarré"
fi

echo "[OK] SSL actif → https://${DOMAIN}"
