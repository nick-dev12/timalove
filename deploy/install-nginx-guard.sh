#!/usr/bin/env bash
# Installe le garde-fou Nginx : si Webuzo réécrit webuzoVH.conf
# (reboot, ajout de domaine, SSL…), le proxy Daphne est recollé tout seul.
set -euo pipefail

REPO_DIR="${REPO_DIR:-/home/colobanes/timalove.goo-bridge.com}"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
PY_SRC="${SRC_DIR}/patch-webuzo-nginx.py"

if [[ "$(id -u)" -ne 0 ]]; then
    echo "À lancer en root : sudo bash deploy/install-nginx-guard.sh" >&2
    exit 1
fi

if [[ ! -f "$PY_SRC" ]]; then
    echo "Script introuvable : $PY_SRC" >&2
    exit 1
fi

install -m 755 "$PY_SRC" /usr/local/sbin/timalove-nginx-patch.py
install -m 644 "${SRC_DIR}/timalove-nginx-patch.service" /etc/systemd/system/timalove-nginx-patch.service
install -m 644 "${SRC_DIR}/timalove-nginx-watch.path" /etc/systemd/system/timalove-nginx-watch.path

cat > /etc/cron.d/timalove-nginx-patch <<'CRON'
# Filet de sécurité si inotify rate un remplacement atomique Webuzo
*/3 * * * * root /usr/bin/python3 /usr/local/sbin/timalove-nginx-patch.py >/dev/null 2>&1
CRON
chmod 644 /etc/cron.d/timalove-nginx-patch

systemctl daemon-reload
systemctl enable timalove-nginx-patch.service timalove-nginx-watch.path
systemctl restart timalove-nginx-watch.path
systemctl start timalove-nginx-patch.service

echo "[OK] Garde-fou Nginx installé."
echo "  watch : systemctl status timalove-nginx-watch.path"
echo "  logs  : journalctl -u timalove-nginx-patch.service -n 30"
echo "  test  : python3 /usr/local/sbin/timalove-nginx-patch.py"
