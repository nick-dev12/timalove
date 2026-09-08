#!/usr/bin/env bash
# =============================================================================
# TIMALOVE — Installation automatique sur VPS Ubuntu (nu)
# Domaine par défaut : mytimalove.com (DNS Cloudflare)
#
# Prérequis :
#   1. SSH root ou sudo sur le VPS (ex. jomas@149.56.140.166)
#   2. Dans Cloudflare, pointer mytimalove.com + www vers l'IP du VPS
#      (enregistrements A, idéalement « DNS only » le temps du SSL)
#
# Usage :
#   # Depuis le VPS (recommandé) — télécharger puis exécuter :
#   curl -fsSL https://raw.githubusercontent.com/nick-dev12/timalove/main/deploy/install-vps.sh \
#     -o /tmp/install-vps.sh
#   sudo bash /tmp/install-vps.sh
#
#   # Ou si le dépôt est déjà cloné :
#   sudo bash /home/jomas/timalove/deploy/install-vps.sh
#
# Options :
#   --domain mytimalove.com
#   --email admin@mytimalove.com     (Let's Encrypt)
#   --app-user jomas
#   --repo-dir /home/jomas/timalove
#   --git-remote https://github.com/nick-dev12/timalove.git
#   --branch main
#   --ssl                            (Certbot après Nginx)
#   --skip-ssl                       (défaut si DNS pas encore prêt)
#   --skip-firewall
#   --skip-clone                     (réutiliser le dépôt existant)
#   --db-password 'xxx'              (sinon généré)
# =============================================================================

set -euo pipefail

DOMAIN="${DOMAIN:-mytimalove.com}"
SSL_EMAIL="${SSL_EMAIL:-admin@${DOMAIN}}"
APP_USER="${APP_USER:-jomas}"
REPO_DIR="${REPO_DIR:-/home/${APP_USER}/timalove}"
DJANGO_DIR="${DJANGO_DIR:-${REPO_DIR}/timalove}"
VENV_DIR="${VENV_DIR:-${REPO_DIR}/venv}"
RUN_DIR="${REPO_DIR}/run"
GIT_REMOTE="${GIT_REMOTE:-https://github.com/nick-dev12/timalove.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
DB_NAME="${DB_NAME:-timalove}"
DB_USER="${DB_USER:-timalove}"
DB_PASSWORD="${DB_PASSWORD:-}"
ENABLE_SSL=false
SKIP_SSL=false
SKIP_FIREWALL=false
SKIP_CLONE=false
VPS_PUBLIC_IP="${VPS_PUBLIC_IP:-}"

usage() {
    sed -n '2,35p' "$0" | sed 's/^# \?//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain)       DOMAIN="$2"; SSL_EMAIL="admin@${DOMAIN}"; shift ;;
        --email)        SSL_EMAIL="$2"; shift ;;
        --app-user)     APP_USER="$2"; REPO_DIR="/home/${APP_USER}/timalove"; DJANGO_DIR="${REPO_DIR}/timalove"; VENV_DIR="${REPO_DIR}/venv"; RUN_DIR="${REPO_DIR}/run"; shift ;;
        --repo-dir)     REPO_DIR="$2"; DJANGO_DIR="${REPO_DIR}/timalove"; VENV_DIR="${REPO_DIR}/venv"; RUN_DIR="${REPO_DIR}/run"; shift ;;
        --git-remote)   GIT_REMOTE="$2"; shift ;;
        --branch)       GIT_BRANCH="$2"; shift ;;
        --db-password)  DB_PASSWORD="$2"; shift ;;
        --ssl)          ENABLE_SSL=true ;;
        --skip-ssl)     SKIP_SSL=true ;;
        --skip-firewall) SKIP_FIREWALL=true ;;
        --skip-clone)   SKIP_CLONE=true ;;
        -h|--help)      usage; exit 0 ;;
        *)              echo "Option inconnue: $1"; usage; exit 1 ;;
    esac
    shift
done

if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

log()  { echo -e "${BLUE}[install-vps]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERREUR]${NC} $*" >&2; }

die() { err "$*"; exit 1; }

require_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        die "Exécutez en root : sudo bash deploy/install-vps.sh"
    fi
}

rand_secret() {
    if command -v openssl &>/dev/null; then
        openssl rand -base64 48 | tr -d '\n/+=' | head -c 64
    else
        head -c 64 /dev/urandom | base64 | tr -d '\n/+=' | head -c 64
    fi
}

detect_public_ip() {
    local ip=""
    for url in \
        "https://ifconfig.me/ip" \
        "https://api.ipify.org" \
        "https://icanhazip.com"; do
        ip=$(curl -4 -fsS --max-time 5 "$url" 2>/dev/null | tr -d '[:space:]' || true)
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "$ip"
            return 0
        fi
    done
    ip=$(hostname -I 2>/dev/null | awk '{print $1}' || true)
    echo "${ip:-}"
}

set_env_var() {
    local file="$1" key="$2" value="$3"
    python3 - "$file" "$key" "$value" <<'PY'
import sys
from pathlib import Path
path, key, value = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
text = path.read_text(encoding="utf-8") if path.exists() else ""
lines = text.splitlines(True)
out, found = [], False
for line in lines:
    if line.startswith(f"{key}=") or line.startswith(f"export {key}="):
        out.append(f"{key}={value}\n")
        found = True
    else:
        out.append(line)
if not found:
    if out and not out[-1].endswith("\n"):
        out[-1] += "\n"
    out.append(f"{key}={value}\n")
path.write_text("".join(out), encoding="utf-8")
PY
}

run_as_app() {
    sudo -u "$APP_USER" bash -lc "$1"
}

django_cmd() {
    run_as_app "cd '$DJANGO_DIR' && source '$VENV_DIR/bin/activate' && $1"
}

write_systemd_unit() {
    local name="$1" content="$2"
    printf '%s\n' "$content" > "/etc/systemd/system/${name}.service"
    ok "Unité systemd : ${name}.service"
}

# ── Début ─────────────────────────────────────────────────────────────────────
require_root

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  TIMALOVE — Installation VPS Ubuntu${NC}"
echo -e "${BOLD}  Domaine : ${DOMAIN}${NC}"
echo -e "${BOLD}  $(date '+%Y-%m-%d %H:%M:%S %Z')${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""

if [[ -z "$VPS_PUBLIC_IP" ]]; then
    VPS_PUBLIC_IP="$(detect_public_ip)"
fi
log "IP publique détectée : ${VPS_PUBLIC_IP:-inconnue}"
log "Utilisateur app      : $APP_USER"
log "Dépôt                : $REPO_DIR"
log "Branche Git          : $GIT_BRANCH"
echo ""

# ── 1. Paquets système ─────────────────────────────────────────────────────────
log "Étape 1/10 — Paquets système (apt)"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    ca-certificates curl gnupg git ufw \
    build-essential pkg-config \
    python3 python3-venv python3-dev python3-pip \
    libpq-dev libjpeg-dev zlib1g-dev libffi-dev \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    >/dev/null

ok "Paquets installés (Python, PostgreSQL, Redis, Nginx, Certbot)"

# ── 2. Utilisateur applicatif ──────────────────────────────────────────────────
log "Étape 2/10 — Utilisateur $APP_USER"

if ! id "$APP_USER" &>/dev/null; then
    useradd --create-home --shell /bin/bash "$APP_USER"
    ok "Utilisateur créé : $APP_USER"
else
    ok "Utilisateur déjà présent : $APP_USER"
fi

# ── 3. Pare-feu ────────────────────────────────────────────────────────────────
log "Étape 3/10 — Pare-feu UFW"

if ! $SKIP_FIREWALL; then
    ufw allow OpenSSH >/dev/null || true
    ufw allow 'Nginx Full' >/dev/null || { ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null; }
    # Active UFW sans bloquer la session SSH en cours
    if ! ufw status | grep -q "Status: active"; then
        ufw --force enable >/dev/null || warn "UFW non activé (à faire manuellement)"
    fi
    ok "UFW : SSH + HTTP/HTTPS"
else
    warn "Pare-feu ignoré (--skip-firewall)"
fi

# ── 4. PostgreSQL ──────────────────────────────────────────────────────────────
log "Étape 4/10 — PostgreSQL"

systemctl enable --now postgresql >/dev/null

if [[ -z "$DB_PASSWORD" ]]; then
    DB_PASSWORD="$(rand_secret | head -c 32)"
fi

sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"
sudo -u postgres psql -c "ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';" >/dev/null

sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};" >/dev/null
# PostgreSQL 15+ : droits sur le schéma public
sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO ${DB_USER};" >/dev/null || true
sudo -u postgres psql -d "$DB_NAME" -c "ALTER SCHEMA public OWNER TO ${DB_USER};" >/dev/null || true

ok "Base ${DB_NAME} / utilisateur ${DB_USER}"

# ── 5. Redis ───────────────────────────────────────────────────────────────────
log "Étape 5/10 — Redis (Channels + Celery)"

REDIS_CONF="/etc/redis/redis.conf"
if [[ -f "$REDIS_CONF" ]]; then
    # Écoute locale uniquement
    sed -i 's/^bind .*/bind 127.0.0.1 ::1/' "$REDIS_CONF" || true
    sed -i 's/^protected-mode no/protected-mode yes/' "$REDIS_CONF" || true
    # Persistance légère (AOF optionnel — on garde RDB par défaut)
    if ! grep -q '^supervised systemd' "$REDIS_CONF"; then
        sed -i 's/^supervised no/supervised systemd/' "$REDIS_CONF" || true
    fi
fi

systemctl enable --now redis-server >/dev/null 2>&1 || systemctl enable --now redis >/dev/null
sleep 1

if redis-cli ping 2>/dev/null | grep -qi PONG; then
    ok "Redis répond PONG"
else
    die "Redis ne répond pas — vérifiez : systemctl status redis-server"
fi

# ── 6. Clone Git ───────────────────────────────────────────────────────────────
log "Étape 6/10 — Code source"

mkdir -p "$(dirname "$REPO_DIR")"
# Si le script tourne depuis un clone temporaire, on conserve SCRIPT_DIR
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if $SKIP_CLONE && [[ -d "$REPO_DIR/.git" ]]; then
    ok "Clone ignoré — dépôt existant"
    run_as_app "cd '$REPO_DIR' && git fetch origin && git checkout '$GIT_BRANCH' && git pull origin '$GIT_BRANCH'" || true
elif [[ -d "$REPO_DIR/.git" ]]; then
    ok "Dépôt déjà présent — mise à jour"
    chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
    run_as_app "cd '$REPO_DIR' && git fetch origin && git checkout '$GIT_BRANCH' && git pull origin '$GIT_BRANCH'"
else
    # Si on exécute depuis le dépôt (SCRIPT_DIR = .../deploy), copier plutôt que re-cloner
    PARENT="$(dirname "$SCRIPT_DIR")"
    if [[ -f "$PARENT/requirements.txt" && -f "$PARENT/timalove/manage.py" && "$PARENT" != "$REPO_DIR" ]]; then
        log "Copie depuis le dépôt local : $PARENT → $REPO_DIR"
        mkdir -p "$REPO_DIR"
        rsync -a --exclude venv --exclude '.git' "$PARENT"/ "$REPO_DIR"/ 2>/dev/null \
            || cp -a "$PARENT"/. "$REPO_DIR"/
        if [[ -d "$PARENT/.git" ]]; then
            cp -a "$PARENT/.git" "$REPO_DIR/.git" 2>/dev/null || true
        fi
        chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
        if [[ ! -d "$REPO_DIR/.git" ]]; then
            run_as_app "git clone --branch '$GIT_BRANCH' '$GIT_REMOTE' '$REPO_DIR'"
        fi
    else
        log "Clonage $GIT_REMOTE → $REPO_DIR"
        mkdir -p "$REPO_DIR"
        chown "$APP_USER:$APP_USER" "$REPO_DIR"
        run_as_app "git clone --branch '$GIT_BRANCH' '$GIT_REMOTE' '$REPO_DIR'"
    fi
fi

if [[ ! -f "$DJANGO_DIR/manage.py" ]]; then
    die "manage.py introuvable : $DJANGO_DIR/manage.py"
fi
ok "Code source prêt"

# ── 7. Python venv + dépendances ───────────────────────────────────────────────
log "Étape 7/10 — Virtualenv + pip"

PYTHON_BIN=""
for cand in python3.12 python3.11 python3.10 python3; do
    if command -v "$cand" &>/dev/null; then
        PYTHON_BIN="$(command -v "$cand")"
        break
    fi
done
[[ -n "$PYTHON_BIN" ]] || die "Python 3.10+ introuvable"

PY_VER="$($PYTHON_BIN -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
log "Python : $PYTHON_BIN ($PY_VER)"

mkdir -p "$RUN_DIR" "$DJANGO_DIR/media" "$DJANGO_DIR/staticfiles"
chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
# Nginx (www-data) doit pouvoir traverser /home/<user> pour servir /static et /media
chmod 755 "/home/$APP_USER" 2>/dev/null || true
chmod -R o+rX "$DJANGO_DIR/staticfiles" "$DJANGO_DIR/media" 2>/dev/null || true

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    run_as_app "$PYTHON_BIN -m venv '$VENV_DIR'"
fi

run_as_app "source '$VENV_DIR/bin/activate' && pip install --upgrade pip -q && pip install -r '$REPO_DIR/requirements.txt'"
ok "Dépendances Python installées"

# ── 8. Fichier .env ────────────────────────────────────────────────────────────
log "Étape 8/10 — Configuration .env"

ENV_FILE="$DJANGO_DIR/.env"
ENV_EXAMPLE="$REPO_DIR/deploy/env.mytimalove.example"
[[ -f "$ENV_EXAMPLE" ]] || ENV_EXAMPLE="$REPO_DIR/deploy/env.production.example"

if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$ENV_EXAMPLE" ]]; then
        cp "$ENV_EXAMPLE" "$ENV_FILE"
    else
        touch "$ENV_FILE"
    fi
fi

SECRET_KEY="$("$VENV_DIR/bin/python" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' 2>/dev/null || rand_secret)"

set_env_var "$ENV_FILE" "SECRET_KEY" "$SECRET_KEY"
set_env_var "$ENV_FILE" "DEBUG" "False"
set_env_var "$ENV_FILE" "ALLOWED_HOSTS" "${DOMAIN},www.${DOMAIN},127.0.0.1"
set_env_var "$ENV_FILE" "SITE_URL" "https://${DOMAIN}"
set_env_var "$ENV_FILE" "CSRF_TRUSTED_ORIGINS" "https://${DOMAIN},https://www.${DOMAIN}"
set_env_var "$ENV_FILE" "SECURE_SSL_REDIRECT" "False"
set_env_var "$ENV_FILE" "SESSION_COOKIE_SECURE" "True"
set_env_var "$ENV_FILE" "CSRF_COOKIE_SECURE" "True"
set_env_var "$ENV_FILE" "USE_X_FORWARDED_HOST" "True"
set_env_var "$ENV_FILE" "DB_NAME" "$DB_NAME"
set_env_var "$ENV_FILE" "DB_USER" "$DB_USER"
set_env_var "$ENV_FILE" "DB_PASSWORD" "$DB_PASSWORD"
set_env_var "$ENV_FILE" "DB_HOST" "127.0.0.1"
set_env_var "$ENV_FILE" "DB_PORT" "5432"
set_env_var "$ENV_FILE" "REDIS_URL" "redis://127.0.0.1:6379/0"
set_env_var "$ENV_FILE" "CELERY_BROKER_URL" "redis://127.0.0.1:6379/0"
set_env_var "$ENV_FILE" "CELERY_RESULT_BACKEND" "redis://127.0.0.1:6379/1"
set_env_var "$ENV_FILE" "USE_REDIS_CHANNELS" "True"
set_env_var "$ENV_FILE" "PAYMENT_SIMULATION" "False"
set_env_var "$ENV_FILE" "NABOOPAY_PRODUCTION_SITE_URL" "https://${DOMAIN}"
set_env_var "$ENV_FILE" "RESEND_FROM_EMAIL" "TimaLove <noreply@${DOMAIN}>"

chown "$APP_USER:$APP_USER" "$ENV_FILE"
chmod 600 "$ENV_FILE"
ok ".env prêt ($ENV_FILE)"

# Chemins pour deploy.sh
mkdir -p /etc/timalove
cat > /etc/timalove/deploy.env <<EOF
# Généré par install-vps.sh — ne pas committer
APP_USER=${APP_USER}
REPO_DIR=${REPO_DIR}
DJANGO_DIR=${DJANGO_DIR}
VENV_DIR=${VENV_DIR}
GIT_BRANCH=${GIT_BRANCH}
SITE_URL=https://${DOMAIN}
DOMAIN=${DOMAIN}
EOF
chmod 644 /etc/timalove/deploy.env
ok "Chemins enregistrés dans /etc/timalove/deploy.env"

# ── 9. Migrations + static + systemd ───────────────────────────────────────────
log "Étape 9/10 — Django + services systemd"

django_cmd "python manage.py migrate --noinput"
django_cmd "python manage.py collectstatic --noinput"
ok "Migrations + collectstatic"

write_systemd_unit "daphne-timalove" "[Unit]
Description=TimaLove Daphne (ASGI HTTP + WebSocket)
After=network.target postgresql.service redis-server.service redis.service
Wants=redis-server.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${DJANGO_DIR}
Environment=DJANGO_SETTINGS_MODULE=config.settings
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-${ENV_FILE}
ExecStart=${VENV_DIR}/bin/daphne \\
    -b 127.0.0.1 \\
    -p 8001 \\
    --proxy-headers \\
    --verbosity 1 \\
    config.asgi:application
Restart=always
RestartSec=3
TimeoutStopSec=15
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target"

write_systemd_unit "celery-timalove" "[Unit]
Description=TimaLove Celery worker
After=network.target redis-server.service redis.service postgresql.service
Wants=redis-server.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${DJANGO_DIR}
Environment=DJANGO_SETTINGS_MODULE=config.settings
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-${ENV_FILE}
ExecStart=${VENV_DIR}/bin/celery \\
    -A config worker \\
    --loglevel=info \\
    --concurrency=4 \\
    --max-tasks-per-child=200
Restart=always
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target"

write_systemd_unit "celerybeat-timalove" "[Unit]
Description=TimaLove Celery beat
After=network.target redis-server.service redis.service
Wants=redis-server.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${DJANGO_DIR}
Environment=DJANGO_SETTINGS_MODULE=config.settings
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-${ENV_FILE}
ExecStart=${VENV_DIR}/bin/celery \\
    -A config beat \\
    --loglevel=info \\
    --schedule=${RUN_DIR}/celerybeat-schedule
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target"

systemctl daemon-reload
systemctl enable --now daphne-timalove celery-timalove celerybeat-timalove
sleep 2

for unit in daphne-timalove celery-timalove celerybeat-timalove; do
    if systemctl is-active --quiet "$unit"; then
        ok "$unit → running"
    else
        err "$unit n'a pas démarré"
        systemctl status "$unit" --no-pager -l || true
        die "Corrigez le service puis relancez : systemctl restart $unit"
    fi
done

# ── 10. Nginx (+ SSL optionnel) ────────────────────────────────────────────────
log "Étape 10/10 — Nginx"

mkdir -p /var/www/certbot
NGINX_TEMPLATE="$REPO_DIR/deploy/nginx-vps.conf.template"
NGINX_SITE="/etc/nginx/sites-available/timalove.conf"

if [[ -f "$NGINX_TEMPLATE" ]]; then
    sed -e "s|__DOMAIN__|${DOMAIN}|g" \
        -e "s|__DJANGO_DIR__|${DJANGO_DIR}|g" \
        "$NGINX_TEMPLATE" > "$NGINX_SITE"
else
    die "Template Nginx manquant : $NGINX_TEMPLATE"
fi

ln -sfn "$NGINX_SITE" /etc/nginx/sites-enabled/timalove.conf
# Désactiver le site default s'il existe
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl enable --now nginx
systemctl reload nginx
ok "Nginx configuré pour ${DOMAIN}"

# SSL
DO_SSL=false
if $ENABLE_SSL && ! $SKIP_SSL; then
    DO_SSL=true
elif ! $SKIP_SSL && ! $ENABLE_SSL; then
    # Auto si le DNS pointe déjà vers ce VPS
    if [[ -n "$VPS_PUBLIC_IP" ]]; then
        DNS_IP=$(getent ahostsv4 "$DOMAIN" 2>/dev/null | awk '{print $1; exit}' || true)
        if [[ "$DNS_IP" == "$VPS_PUBLIC_IP" ]]; then
            log "DNS ${DOMAIN} → ${DNS_IP} (OK) — tentative SSL automatique"
            DO_SSL=true
        else
            warn "DNS ${DOMAIN} → ${DNS_IP:-?} (attendu ${VPS_PUBLIC_IP}) — SSL reporté"
            warn "Après mise à jour Cloudflare, relancez :"
            warn "  sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos -m ${SSL_EMAIL} --redirect"
        fi
    fi
fi

if $DO_SSL; then
    log "Certificat Let's Encrypt (Certbot)"
    if certbot --nginx \
        -d "$DOMAIN" -d "www.${DOMAIN}" \
        --non-interactive --agree-tos \
        -m "$SSL_EMAIL" \
        --redirect; then
        set_env_var "$ENV_FILE" "SECURE_SSL_REDIRECT" "True"
        set_env_var "$ENV_FILE" "SECURE_HSTS_SECONDS" "31536000"
        systemctl restart daphne-timalove
        ok "SSL actif + SECURE_SSL_REDIRECT=True"
    else
        warn "Certbot a échoué — site accessible en HTTP pour l'instant"
    fi
fi

# ── Vérifications ──────────────────────────────────────────────────────────────
echo ""
log "Vérifications"
HTTP_LOCAL=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $DOMAIN" --max-time 8 http://127.0.0.1:8001/ || echo "000")
if [[ "$HTTP_LOCAL" == "200" || "$HTTP_LOCAL" == "302" || "$HTTP_LOCAL" == "301" ]]; then
    ok "Daphne local → HTTP $HTTP_LOCAL"
else
    warn "Daphne local → HTTP $HTTP_LOCAL (journalctl -u daphne-timalove -n 50)"
fi

if redis-cli ping 2>/dev/null | grep -qi PONG; then
    ok "Redis OK"
fi

echo ""
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Installation terminée${NC}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""
log "Site     : https://${DOMAIN}  (ou http:// tant que SSL n'est pas actif)"
log "Admin    : https://${DOMAIN}/espace-prive/connexion/"
log "Logs     : journalctl -u daphne-timalove -f"
log "Updates  : sudo bash ${DJANGO_DIR}/deploy.sh"
echo ""
echo -e "${BOLD}Cloudflare — DNS à configurer maintenant :${NC}"
echo "  1. Supprimer les CNAME Vercel de ${DOMAIN} et www.${DOMAIN}"
echo "  2. Créer :"
echo "       Type A    Nom @     Contenu ${VPS_PUBLIC_IP:-VOTRE_IP_VPS}   Proxy : DNS only (gris) le temps du SSL"
echo "       Type A    Nom www   Contenu ${VPS_PUBLIC_IP:-VOTRE_IP_VPS}   Proxy : DNS only"
echo "  3. Garder les enregistrements mail (MX/TXT SES, mail.*, etc.)"
echo "  4. SSL/TLS Cloudflare → mode Full (strict) une fois Certbot OK"
echo "  5. Puis éventuellement réactiver le proxy orange"
echo ""
echo -e "${BOLD}À finaliser sur le serveur :${NC}"
echo "  nano ${ENV_FILE}"
echo "    → NabooPay, Resend, Firebase, reCAPTCHA…"
echo "  Copier les secrets hors git dans ${DJANGO_DIR}/ :"
echo "    timalove-ddaa5-*.json , AuthKey_*.p8 , google-services.json"
echo "  Puis : sudo bash ${DJANGO_DIR}/deploy.sh --skip-git"
echo ""
echo "  Compte super-admin (si besoin) :"
echo "    sudo -u ${APP_USER} bash -lc \"cd ${DJANGO_DIR} && source ${VENV_DIR}/bin/activate && python manage.py createsuperuser\""
echo ""
echo -e "${YELLOW}Mot de passe PostgreSQL (conservez-le) : enregistré dans ${ENV_FILE}${NC}"
echo ""
