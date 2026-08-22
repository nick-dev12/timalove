#!/usr/bin/env bash
# =============================================================================
# TIMALOVE — Installation initiale sur VPS Webuzo
# À lancer UNE FOIS en root, après le git clone dans le document root.
#
#   sudo bash /home/colobanes/timalove.goo-bridge.com/deploy/bootstrap.sh
#
# Ensuite, les mises à jour se font avec :
#   sudo bash /home/colobanes/timalove.goo-bridge.com/timalove/deploy.sh
# =============================================================================

set -euo pipefail

APP_USER="${APP_USER:-colobanes}"
REPO_DIR="${REPO_DIR:-/home/colobanes/timalove.goo-bridge.com}"
DJANGO_DIR="${DJANGO_DIR:-${REPO_DIR}/timalove}"
VENV_DIR="${VENV_DIR:-${REPO_DIR}/venv}"
RUN_DIR="${REPO_DIR}/run"
DOMAIN="${DOMAIN:-timalove.goo-bridge.com}"
GIT_REMOTE="${GIT_REMOTE:-https://github.com/nick-dev12/timalove.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"

if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

log()  { echo -e "${BLUE}[bootstrap]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERREUR]${NC} $*" >&2; }

if [[ "$(id -u)" -ne 0 ]]; then
    err "Ce script doit être exécuté en root : sudo bash deploy/bootstrap.sh"
    exit 1
fi

if ! id "$APP_USER" &>/dev/null; then
    err "Utilisateur introuvable : $APP_USER"
    exit 1
fi

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  TIMALOVE — Installation initiale${NC}"
echo -e "${BOLD}  $DOMAIN${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""

# ── 1. Dépôt Git ───────────────────────────────────────────────────────────────
log "Étape 1/8 — Dépôt Git"

mkdir -p "$REPO_DIR"
chown "$APP_USER:$APP_USER" "$REPO_DIR"

if [[ ! -d "$REPO_DIR/.git" ]]; then
    log "Clonage de $GIT_REMOTE → $REPO_DIR"
    BACKUP_DEFAULT="$REPO_DIR/.webuzo-default-backup"
    mkdir -p "$BACKUP_DEFAULT"
    for f in cgi-bin index.html index.php default.php; do
        if [[ -e "$REPO_DIR/$f" ]]; then
            mv "$REPO_DIR/$f" "$BACKUP_DEFAULT/"
            warn "Fichier Webuzo déplacé : $f → $BACKUP_DEFAULT/"
        fi
    done
    TMP_CLONE="$(mktemp -d /tmp/timalove-clone.XXXXXX)"
    git clone --branch "$GIT_BRANCH" "$GIT_REMOTE" "$TMP_CLONE"
    cp -a "$TMP_CLONE"/. "$REPO_DIR"/
    rm -rf "$TMP_CLONE"
    chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
else
    ok "Dépôt déjà présent"
    sudo -u "$APP_USER" bash -lc "cd '$REPO_DIR' && git fetch origin && git checkout '$GIT_BRANCH' && git pull origin '$GIT_BRANCH'"
fi

if [[ ! -f "$DJANGO_DIR/manage.py" ]]; then
    err "manage.py introuvable après clone : $DJANGO_DIR/manage.py"
    exit 1
fi
ok "Code source prêt"

# ── 2. Python / venv ───────────────────────────────────────────────────────────
log "Étape 2/8 — Environnement virtuel Python"

PYTHON_BIN=""
for cand in python3.12 python3.11 python3.10 python3; do
    if command -v "$cand" &>/dev/null; then
        PYTHON_BIN="$(command -v "$cand")"
        break
    fi
done

if [[ -z "$PYTHON_BIN" ]]; then
    err "Python 3 introuvable. Installez Python 3.10+ (Webuzo → Applications, ou yum/apt)."
    exit 1
fi

PY_VER="$($PYTHON_BIN -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
log "Python détecté : $PYTHON_BIN ($PY_VER)"
if [[ "${PY_VER%%.*}" -lt 3 ]] || { [[ "${PY_VER%%.*}" -eq 3 ]] && [[ "${PY_VER#*.}" -lt 10 ]]; }; then
    err "Django 5.2 exige Python 3.10 ou plus (trouvé $PY_VER)."
    exit 1
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    sudo -u "$APP_USER" "$PYTHON_BIN" -m venv "$VENV_DIR"
    ok "venv créé : $VENV_DIR"
else
    ok "venv déjà présent"
fi

sudo -u "$APP_USER" bash -lc "source '$VENV_DIR/bin/activate' && pip install --upgrade pip -q && pip install -r '$REPO_DIR/requirements.txt'"
ok "Dépendances installées"

# ── 3. Dossiers runtime / médias ───────────────────────────────────────────────
log "Étape 3/8 — Dossiers media / run / staticfiles"

mkdir -p "$RUN_DIR" "$DJANGO_DIR/media" "$DJANGO_DIR/staticfiles"
chown -R "$APP_USER:$APP_USER" "$RUN_DIR" "$DJANGO_DIR/media" "$DJANGO_DIR/staticfiles"
chmod 775 "$RUN_DIR" "$DJANGO_DIR/media"
ok "Dossiers créés"

# ── 4. Fichier .env ────────────────────────────────────────────────────────────
log "Étape 4/8 — Fichier .env production"

ENV_FILE="$DJANGO_DIR/.env"
ENV_EXAMPLE="$REPO_DIR/deploy/env.production.example"

if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$ENV_EXAMPLE" ]]; then
        sudo -u "$APP_USER" cp "$ENV_EXAMPLE" "$ENV_FILE"
        GEN_KEY="$("$VENV_DIR/bin/python" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
        if grep -q '^SECRET_KEY=' "$ENV_FILE"; then
            # Remplace uniquement la ligne SECRET_KEY sans toucher au reste
            sudo -u "$APP_USER" python3 - "$ENV_FILE" "$GEN_KEY" <<'PY'
import sys
from pathlib import Path
path, key = Path(sys.argv[1]), sys.argv[2]
text = path.read_text(encoding="utf-8")
lines = []
for line in text.splitlines(True):
    if line.startswith("SECRET_KEY="):
        lines.append(f"SECRET_KEY={key}\n")
    else:
        lines.append(line)
path.write_text("".join(lines), encoding="utf-8")
PY
        fi
        warn "Fichier .env créé. ÉDITEZ-LE avant de continuer si ce n'est pas déjà fait :"
        warn "  nano $ENV_FILE"
        warn "Champs obligatoires : DB_PASSWORD, SECRET_KEY (déjà généré), clés CinetPay/Firebase."
    else
        err "Modèle introuvable : $ENV_EXAMPLE"
        exit 1
    fi
else
    ok ".env déjà présent (non écrasé)"
fi

if grep -q 'REMPLACER-MOT-DE-PASSE-POSTGRES' "$ENV_FILE"; then
    err "DB_PASSWORD n'est pas encore renseigné dans $ENV_FILE"
    err "Éditez le fichier, puis relancez bootstrap.sh"
    exit 1
fi

# ── 5. Django migrate + collectstatic ──────────────────────────────────────────
log "Étape 5/8 — Migrations + fichiers statiques"

run_django() {
    sudo -u "$APP_USER" bash -lc "cd '$DJANGO_DIR' && source '$VENV_DIR/bin/activate' && $1"
}

run_django "python manage.py migrate --noinput"
run_django "python manage.py collectstatic --noinput"
ok "Base et static OK"

# ── 6. systemd ─────────────────────────────────────────────────────────────────
log "Étape 6/8 — Services systemd"

UNIT_SRC="$REPO_DIR/deploy"
for unit in daphne-timalove celery-timalove celerybeat-timalove; do
    if [[ -f "$UNIT_SRC/${unit}.service" ]]; then
        cp "$UNIT_SRC/${unit}.service" "/etc/systemd/system/${unit}.service"
        ok "Installé : ${unit}.service"
    else
        err "Unité manquante : $UNIT_SRC/${unit}.service"
        exit 1
    fi
done

systemctl daemon-reload
systemctl enable --now daphne-timalove celery-timalove celerybeat-timalove
sleep 2

for unit in daphne-timalove celery-timalove celerybeat-timalove; do
    if systemctl is-active --quiet "$unit"; then
        ok "$unit → running"
    else
        err "$unit n'a pas démarré"
        systemctl status "$unit" --no-pager -l || true
        exit 1
    fi
done

# ── 7. Nginx Webuzo ────────────────────────────────────────────────────────────
log "Étape 7/8 — Configuration Nginx"

NGINX_CONF_DIR=""
NGINX_BIN=""
for d in /usr/local/apps/nginx/etc/conf.d /etc/nginx/conf.d; do
    if [[ -d "$d" ]]; then
        NGINX_CONF_DIR="$d"
        break
    fi
done
for b in /usr/local/apps/nginx/sbin/nginx /usr/sbin/nginx nginx; do
    if command -v "$b" &>/dev/null || [[ -x "$b" ]]; then
        NGINX_BIN="$b"
        break
    fi
done

if [[ -z "$NGINX_CONF_DIR" ]]; then
    warn "Dossier conf.d Nginx introuvable."
else
    # Ne jamais déplacer webuzoVH.conf (vhost global Webuzo).
    # On patche uniquement les server { } TimaLove, puis on installe
    # le garde-fou systemd/cron qui re-colle le proxy si Webuzo réécrit le fichier.
    rm -f "$NGINX_CONF_DIR/timalove-django.conf"
    if [[ -f "$REPO_DIR/deploy/patch-webuzo-nginx.py" ]]; then
        python3 "$REPO_DIR/deploy/patch-webuzo-nginx.py" || warn "patch-webuzo-nginx.py a échoué"
    fi
    if [[ -f "$REPO_DIR/deploy/install-nginx-guard.sh" ]]; then
        bash "$REPO_DIR/deploy/install-nginx-guard.sh" || warn "install-nginx-guard.sh a échoué"
    fi
    ok "Proxy Daphne + garde-fou Webuzo"

    TEST_OK=false
    if [[ -n "$NGINX_BIN" && -x "$NGINX_BIN" ]]; then
        if "$NGINX_BIN" -t 2>/dev/null; then
            TEST_OK=true
        fi
    elif command -v nginx &>/dev/null && nginx -t 2>/dev/null; then
        TEST_OK=true
    fi

    if $TEST_OK; then
        if command -v service &>/dev/null; then
            service nginx reload || "$NGINX_BIN" -s reload || true
        else
            "$NGINX_BIN" -s reload || systemctl reload nginx || true
        fi
        ok "Nginx rechargé"
    else
        warn "nginx -t a échoué. Vérifiez la config avant de recharger."
        warn "Si conflit de server_name, inspectez : grep -r $DOMAIN $NGINX_CONF_DIR"
    fi
fi

# ── 8. Vérifications ───────────────────────────────────────────────────────────
log "Étape 8/8 — Vérifications"

if command -v ss &>/dev/null; then
    if ss -ltn | grep -q ':8001'; then
        ok "Daphne écoute sur 127.0.0.1:8001"
    else
        warn "Port 8001 non visible (Daphne a-t-il bien démarré ?)"
    fi
fi

HTTP_LOCAL=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $DOMAIN" --max-time 8 http://127.0.0.1:8001/ || echo "000")
if [[ "$HTTP_LOCAL" == "200" || "$HTTP_LOCAL" == "302" || "$HTTP_LOCAL" == "301" ]]; then
    ok "Daphne répond en local → $HTTP_LOCAL"
else
    warn "Daphne local → HTTP $HTTP_LOCAL (vérifiez journalctl -u daphne-timalove)"
fi

echo ""
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Installation initiale terminée${NC}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""
log "Site   : http://$DOMAIN  (activez ensuite SSL dans Webuzo)"
log "Admin  : http://$DOMAIN/espace-prive/connexion/"
log "Logs   : journalctl -u daphne-timalove -f"
log "Update : sudo bash $DJANGO_DIR/deploy.sh"
echo ""
log "À faire encore :"
echo "  1. nano $ENV_FILE   (Firebase JSON, CinetPay, email)"
echo "  2. Copier timalove-ddaa5-*.json et AuthKey_*.p8 dans $DJANGO_DIR (hors git)"
echo "  3. Webuzo → SSL : activer Let's Encrypt pour $DOMAIN"
echo "  4. Décommenter le bloc HTTPS dans $NGINX_CONF_DIR/timalove-django.conf"
echo "  5. Dans .env : SECURE_SSL_REDIRECT=True puis : sudo bash $DJANGO_DIR/deploy.sh --skip-git"
echo "  6. python manage.py seed_site  (compte admin initial, si besoin)"
echo ""
