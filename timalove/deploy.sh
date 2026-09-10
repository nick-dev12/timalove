#!/usr/bin/env bash
# =============================================================================
# TIMALOVE — Mise à jour production (VPS Ubuntu / mytimalove.com)
#
# À utiliser pour CHAQUE déploiement après l’install initiale :
#   sudo bash /home/jomas/timalove/timalove/deploy.sh
#
# Fait par défaut (sans option) :
#   git pull → pip → migrate → collectstatic → restart services
#   puis vérifie TOUJOURS (--no-checks pour désactiver) :
#   systemd, Redis, Nginx, Daphne :8001, HTTP, static, API push/notifs/messages,
#   verify_runtime (Redis Channels, Celery, WebSocket, FCM),
#   django check --deploy, NabooPay (si clés présentes)
#
# Options :
#   --fast            git pull + collectstatic seulement (sans restart / checks lourds)
#   --skip-naboopay   ignorer NabooPay (utile avant d’avoir les clés)
#   --strict          tout WARN devient ERREUR (exit 1)
#   --no-checks       désactiver les vérifications finales (déconseillé)
#
# Premier install : sudo bash deploy/install-vps.sh
# =============================================================================

set -euo pipefail

# Chemins générés par deploy/install-vps.sh
if [[ -f /etc/timalove/deploy.env ]]; then
    # shellcheck disable=SC1091
    source /etc/timalove/deploy.env
fi

# ── Configuration ─────────────────────────────────────────────────────────────
if [[ -z "${APP_USER:-}" ]]; then
    if id colobanes &>/dev/null && [[ -d /home/colobanes/timalove.goo-bridge.com ]]; then
        APP_USER=colobanes
        REPO_DIR="${REPO_DIR:-/home/colobanes/timalove.goo-bridge.com}"
        SITE_URL="${SITE_URL:-https://timalove.goo-bridge.com}"
    else
        APP_USER=jomas
        REPO_DIR="${REPO_DIR:-/home/jomas/timalove}"
        SITE_URL="${SITE_URL:-https://mytimalove.com}"
    fi
fi
REPO_DIR="${REPO_DIR:-/home/${APP_USER}/timalove}"
DJANGO_DIR="${DJANGO_DIR:-${REPO_DIR}/timalove}"
VENV_DIR="${VENV_DIR:-${REPO_DIR}/venv}"
GIT_BRANCH="${GIT_BRANCH:-main}"
SITE_URL="${SITE_URL:-https://mytimalove.com}"
SETTINGS_FILE="timalove/config/settings.py"
CHECK_URL="$SITE_URL"

REQUIRED_SERVICES=(
    "daphne-timalove"
    "celery-timalove"
)
OPTIONAL_SERVICES=(
    "celerybeat-timalove"
)
INFRA_SERVICES=(
    "redis-server"
    "nginx"
)

# ── Options ────────────────────────────────────────────────────────────────────
SKIP_PIP=false
SKIP_MIGRATE=false
SKIP_STATIC=false
SKIP_RESTART=false
SKIP_GIT=false
FAST_MODE=false
RESET_SETTINGS=false
RUN_CHECKS=true
SKIP_NABOOPAY=false
STRICT_MODE=false
DEPLOY_FAILED=false

usage() {
    cat <<'EOF'
Usage: deploy.sh [OPTIONS]

Déploie la dernière version depuis GitHub, redémarre les services et vérifie
static / Redis / temps réel (WebSocket) / notifications / Celery / HTTP.

Options:
  --fast              Déploiement rapide : git pull + collectstatic uniquement
  --skip-pip          Ne pas exécuter pip install
  --skip-migrate      Ne pas exécuter migrate
  --skip-static       Ne pas exécuter collectstatic
  --skip-restart      Ne pas redémarrer Daphne/Celery
  --skip-git          Ne pas faire git pull
  --reset-settings    Abandonner les modifs locales de settings.py avant pull
  --no-checks         Pas de vérifications finales (déconseillé)
  --skip-naboopay     Ne pas vérifier NabooPay
  --strict            Échec si une vérification critique est en WARN/FAIL
  -h, --help          Afficher cette aide

Exemples:
  sudo bash /home/jomas/timalove/timalove/deploy.sh
  sudo bash /home/jomas/timalove/timalove/deploy.sh --skip-naboopay
  sudo bash /home/jomas/timalove/timalove/deploy.sh --strict
  sudo bash /home/jomas/timalove/timalove/deploy.sh --fast
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fast)           FAST_MODE=true; SKIP_PIP=true; SKIP_MIGRATE=true; SKIP_RESTART=true ;;
        --skip-pip)       SKIP_PIP=true ;;
        --skip-migrate)   SKIP_MIGRATE=true ;;
        --skip-static)    SKIP_STATIC=true ;;
        --skip-restart)   SKIP_RESTART=true ;;
        --skip-git)       SKIP_GIT=true ;;
        --reset-settings) RESET_SETTINGS=true ;;
        --no-checks)      RUN_CHECKS=false ;;
        --skip-naboopay)  SKIP_NABOOPAY=true ;;
        --strict)         STRICT_MODE=true ;;
        -h|--help)        usage; exit 0 ;;
        *)                echo "Option inconnue: $1"; usage; exit 1 ;;
    esac
    shift
done

# ── Couleurs ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

log()  { echo -e "${BLUE}[deploy]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; if $STRICT_MODE; then DEPLOY_FAILED=true; fi; }
err()  { echo -e "${RED}[ERREUR]${NC} $*" >&2; DEPLOY_FAILED=true; }

detect_public_ip() {
    local ip=""
    for url in "https://ifconfig.me/ip" "https://api.ipify.org" "https://icanhazip.com"; do
        ip=$(curl -4 -fsS --max-time 4 "$url" 2>/dev/null | tr -d '[:space:]' || true)
        if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo "$ip"
            return 0
        fi
    done
    hostname -I 2>/dev/null | awk '{print $1}'
}

resolve_site_url_from_env() {
    local env_file="$DJANGO_DIR/.env" val=""
    [[ -f "$env_file" ]] || return 0
    val=$(grep -E '^SITE_URL=' "$env_file" | tail -1 | cut -d= -f2- | tr -d '\r' | sed 's/^["'\'']//;s/["'\'']$//' || true)
    if [[ -n "$val" ]]; then
        SITE_URL="$val"
    fi
}

resolve_check_url() {
    local domain ip dns_ip
    resolve_site_url_from_env
    CHECK_URL="$SITE_URL"
    ip="$(detect_public_ip)"
    domain="$(echo "$SITE_URL" | sed -E 's#https?://##' | cut -d/ -f1 | cut -d: -f1)"
    if [[ -n "$ip" && -n "$domain" && ! "$domain" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        dns_ip=$(getent ahostsv4 "$domain" 2>/dev/null | awk '{print $1; exit}' || true)
        if [[ -n "$dns_ip" && "$dns_ip" != "$ip" ]]; then
            warn "DNS $domain → $dns_ip (VPS=$ip) — checks HTTP via http://$ip"
            CHECK_URL="http://${ip}"
        fi
    fi
}

# ── Vérifications préalables ───────────────────────────────────────────────────
if [[ "$(id -u)" -ne 0 ]]; then
    err "Ce script doit être exécuté en root (ou via sudo)."
    err "Exemple : sudo bash /home/jomas/timalove/timalove/deploy.sh"
    exit 1
fi

if ! id "$APP_USER" &>/dev/null; then
    err "Utilisateur introuvable : $APP_USER"
    exit 1
fi

if [[ ! -d "$REPO_DIR/.git" ]]; then
    err "Dépôt Git introuvable : $REPO_DIR"
    err "Lancez d'abord : sudo bash deploy/install-vps.sh"
    exit 1
fi

if [[ ! -f "$DJANGO_DIR/manage.py" ]]; then
    err "Projet Django introuvable : $DJANGO_DIR/manage.py"
    exit 1
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    err "Virtualenv introuvable : $VENV_DIR"
    err "Lancez d'abord : sudo bash deploy/install-vps.sh"
    exit 1
fi

if [[ ! -f "$DJANGO_DIR/.env" ]]; then
    err "Fichier .env manquant : $DJANGO_DIR/.env"
    err "Copiez deploy/env.mytimalove.example vers timalove/.env et remplissez les secrets."
    exit 1
fi

resolve_check_url

run_as_app() {
    sudo -u "$APP_USER" bash -lc "$1"
}

django_cmd() {
    run_as_app "cd '$DJANGO_DIR' && source '$VENV_DIR/bin/activate' && $1"
}

clean_untracked_pull_blockers() {
    local blockers f
    blockers=$(run_as_app "cd '$REPO_DIR' && git ls-files --others --exclude-standard" || true)
    [[ -z "$blockers" ]] && return 0

    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        if run_as_app "cd '$REPO_DIR' && git cat-file -e 'origin/$GIT_BRANCH:$f' 2>/dev/null"; then
            warn "Doublon local non suivi (remplacé par Git) : $f"
            run_as_app "cd '$REPO_DIR' && rm -rf '$f'"
        fi
    done <<< "$blockers"
}

# ── En-tête ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}  TIMALOVE — Déploiement${NC}"
echo -e "${BOLD}  $(date '+%Y-%m-%d %H:%M:%S %Z')${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""
log "Dépôt     : $REPO_DIR"
log "Django    : $DJANGO_DIR"
log "Utilisateur app : $APP_USER"
log "Branche   : $GIT_BRANCH"
log "SITE_URL  : $SITE_URL"
log "Checks    : $CHECK_URL"
if $FAST_MODE; then warn "Mode rapide (--fast) : static uniquement, pas de restart"; fi
if $STRICT_MODE; then warn "Mode strict (--strict) : tout WARN = échec"; fi
echo ""

# ── 1. Git pull ────────────────────────────────────────────────────────────────
if ! $SKIP_GIT; then
    log "Étape 1/5 — Git pull"

    if $RESET_SETTINGS; then
        warn "Abandon des modifications locales de $SETTINGS_FILE"
        run_as_app "cd '$REPO_DIR' && git checkout -- '$SETTINGS_FILE'" || true
    fi

    if ! $RESET_SETTINGS; then
        if ! run_as_app "cd '$REPO_DIR' && git diff --quiet -- '$SETTINGS_FILE'" 2>/dev/null; then
            if run_as_app "cd '$REPO_DIR' && git diff -- '$SETTINGS_FILE' | grep -q ."; then
                warn "$SETTINGS_FILE modifié localement sur le VPS."
                warn "Relancez avec --reset-settings pour abandonner ces changements."
                warn "Ou manuellement : git checkout -- $SETTINGS_FILE"
                exit 1
            fi
        fi
    fi

    clean_untracked_pull_blockers
    PRE_PULL_HEAD=$(run_as_app "cd '$REPO_DIR' && git rev-parse HEAD")
    run_as_app "cd '$REPO_DIR' && git fetch origin && git pull origin '$GIT_BRANCH'"
    POST_PULL_HEAD=$(run_as_app "cd '$REPO_DIR' && git rev-parse HEAD")
    ok "Code à jour ($(run_as_app "cd '$REPO_DIR' && git rev-parse --short HEAD"))"

    if [[ "$PRE_PULL_HEAD" != "$POST_PULL_HEAD" && -z "${DEPLOY_REEXEC:-}" ]]; then
        DEPLOY_SCRIPT="$REPO_DIR/timalove/deploy.sh"
        if [[ -f "$DEPLOY_SCRIPT" ]] && run_as_app "cd '$REPO_DIR' && git diff --name-only '$PRE_PULL_HEAD' '$POST_PULL_HEAD'" | grep -qE '(^|/)deploy\.sh$|(^|/)deploy/verify_runtime\.py$'; then
            warn "Script de déploiement mis à jour — relance automatique"
            DEPLOY_REEXEC=1 exec bash "$DEPLOY_SCRIPT" "$@"
        fi
    fi
else
    log "Étape 1/5 — Git pull (ignoré)"
fi

DEPLOY_HEAD=$(run_as_app "cd '$REPO_DIR' && git rev-parse --short HEAD" 2>/dev/null || echo "local")
echo "$DEPLOY_HEAD" > "$DJANGO_DIR/deploy-revision.txt"
ok "Révision deploy : $DEPLOY_HEAD"

# ── 2. pip install ─────────────────────────────────────────────────────────────
if ! $SKIP_PIP; then
    log "Étape 2/5 — pip install"
    run_as_app "cd '$REPO_DIR' && source '$VENV_DIR/bin/activate' && pip install -r requirements.txt -q"
    ok "Dépendances Python à jour"
else
    log "Étape 2/5 — pip install (ignoré)"
fi

# ── 3. Migrations ──────────────────────────────────────────────────────────────
if ! $SKIP_MIGRATE; then
    log "Étape 3/5 — Migrations Django"
    MIGRATE_OUTPUT=$(django_cmd "python manage.py migrate --noinput" 2>&1) || {
        err "Échec migrate"
        echo "$MIGRATE_OUTPUT"
        if echo "$MIGRATE_OUTPUT" | grep -q "must be owner of table"; then
            warn "PostgreSQL : l'utilisateur Django n'est pas propriétaire des tables."
            warn "Corrigez puis relancez : sudo bash $REPO_DIR/deploy/fix-db-ownership.sh --then-deploy"
        fi
        exit 1
    }
    echo "$MIGRATE_OUTPUT"
    if echo "$MIGRATE_OUTPUT" | grep -q "not yet reflected in a migration"; then
        warn "Des modèles ont changé sans migration — créez-les sur le PC (makemigrations) puis repush."
    fi
    ok "Migrations appliquées"
else
    log "Étape 3/5 — Migrations (ignorées)"
fi

# ── 4. Fichiers statiques ──────────────────────────────────────────────────────
if ! $SKIP_STATIC; then
    log "Étape 4/5 — collectstatic"
    STATIC_OUTPUT=$(django_cmd "python manage.py collectstatic --noinput" 2>&1)
    echo "$STATIC_OUTPUT"
    if [[ ! -d "$DJANGO_DIR/staticfiles" ]] || [[ -z "$(ls -A "$DJANGO_DIR/staticfiles" 2>/dev/null || true)" ]]; then
        err "staticfiles vide après collectstatic"
        exit 1
    fi
    ok "Fichiers statiques publiés ($(find "$DJANGO_DIR/staticfiles" -type f 2>/dev/null | wc -l) fichiers)"
    # Nginx (www-data) doit lire staticfiles / media
    chmod 755 "/home/$APP_USER" 2>/dev/null || true
    chmod -R o+rX "$DJANGO_DIR/staticfiles" 2>/dev/null || true
    [[ -d "$DJANGO_DIR/media" ]] && chmod -R o+rX "$DJANGO_DIR/media" 2>/dev/null || true
else
    log "Étape 4/5 — collectstatic (ignoré)"
fi

service_unit_exists() {
    local svc="$1"
    systemctl cat "${svc}.service" &>/dev/null \
        || systemctl is-enabled "${svc}" &>/dev/null \
        || [[ -f "/etc/systemd/system/${svc}.service" ]]
}

restart_service() {
    local svc="$1" required="$2"
    if service_unit_exists "$svc"; then
        systemctl restart "$svc"
        ok "Redémarré : $svc"
        return 0
    fi
    if [[ "$required" == "required" ]]; then
        err "Service requis non installé : $svc"
        err "Lancez : sudo bash $REPO_DIR/deploy/install-vps.sh"
        exit 1
    fi
    warn "Service optionnel absent : $svc (tâches planifiées Celery Beat)"
    return 1
}

# ── 5. Redémarrage services ────────────────────────────────────────────────────
if ! $SKIP_RESTART; then
    log "Étape 5/5 — Redémarrage services systemd"
    for svc in "${REQUIRED_SERVICES[@]}"; do
        restart_service "$svc" required
    done
    for svc in "${OPTIONAL_SERVICES[@]}"; do
        restart_service "$svc" optional || true
    done
    log "Redémarrage infrastructure (Redis, Nginx)"
    for svc in "${INFRA_SERVICES[@]}"; do
        if service_unit_exists "$svc"; then
            if [[ "$svc" == "nginx" ]] && ! nginx -t 2>/dev/null; then
                warn "nginx -t a échoué — restart Nginx ignoré"
                continue
            fi
            restart_service "$svc" optional || true
        else
            warn "Service infra absent : $svc"
        fi
    done
    sleep 2
else
    log "Étape 5/5 — Redémarrage services (ignoré)"
fi

# ── Patch Nginx WebSocket (Webuzo uniquement) ──────────────────────────────────
NGINX_PATCH="$REPO_DIR/deploy/patch-webuzo-nginx.py"
NGINX_CONF="/usr/local/apps/nginx/etc/conf.d/webuzoVH.conf"
if [[ -f "$NGINX_PATCH" ]] && [[ -f "$NGINX_CONF" ]]; then
    log "Patch Nginx WebSocket (proxy wss → Daphne / Webuzo)"
    if python3 "$NGINX_PATCH"; then
        ok "Nginx WebSocket proxy → appliqué (v4)"
    else
        warn "Patch Nginx WebSocket — échec (lancer : sudo python3 $NGINX_PATCH)"
    fi
fi

check_service_active() {
    local svc="$1" required="$2"
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        ok "$svc → active (running)"
        return 0
    fi
    if service_unit_exists "$svc"; then
        err "$svc → inactif ou en erreur"
        systemctl status "$svc" --no-pager -l || true
        return 1
    fi
    if [[ "$required" == "required" ]]; then
        err "$svc → unit systemd absente"
        return 1
    fi
    warn "$svc → non installé (optionnel)"
    return 0
}

# ── Vérifications finales ──────────────────────────────────────────────────────
echo ""
log "Vérifications finales (services, temps réel, notifications)"
echo ""

if $RUN_CHECKS; then
    for svc in "${REQUIRED_SERVICES[@]}"; do
        check_service_active "$svc" required || true
    done
    for svc in "${OPTIONAL_SERVICES[@]}"; do
        check_service_active "$svc" optional || true
    done

    if systemctl is-active --quiet nginx 2>/dev/null; then
        ok "Nginx → active"
    else
        warn "Nginx non actif"
    fi

    if command -v redis-cli &>/dev/null && redis-cli ping 2>/dev/null | grep -qi PONG; then
        ok "Redis → PONG (Channels + Celery)"
    else
        err "Redis ne répond pas — temps réel / Celery impactés"
    fi

    if systemctl is-active --quiet postgresql 2>/dev/null; then
        ok "PostgreSQL → active"
    else
        warn "PostgreSQL service non détecté (vérifiez manuellement)"
    fi

    DAPHNE_PORT="${DAPHNE_PORT:-8001}"
    if command -v ss &>/dev/null && ss -ltn 2>/dev/null | grep -q ":${DAPHNE_PORT}"; then
        ok "Daphne écoute sur :${DAPHNE_PORT}"
    else
        err "Port ${DAPHNE_PORT} non visible — WebSocket indisponible"
    fi

    if command -v curl &>/dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$CHECK_URL/" || echo "000")
        if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "405" ]]; then
            ok "Site HTTP → $HTTP_CODE ($CHECK_URL)"
        else
            err "Site HTTP → $HTTP_CODE (attendu 200/301/302/405) — URL: $CHECK_URL"
        fi

        STATIC_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$CHECK_URL/static/css/timalove.css" || echo "000")
        if [[ "$STATIC_CODE" == "200" ]]; then
            ok "Static CSS → 200"
        else
            warn "Static CSS → $STATIC_CODE (collectstatic / Nginx alias ?)"
        fi

        PUSH_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$CHECK_URL/api/push/config/" || echo "000")
        if [[ "$PUSH_CODE" == "200" ]]; then
            ok "API push/config → 200"
        else
            err "API push/config → $PUSH_CODE"
        fi

        for api_path in "/api/notifications/unread-count/" "/api/messages/unread-count/"; do
            API_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 "$CHECK_URL${api_path}" || echo "000")
            if [[ "$API_CODE" == "200" || "$API_CODE" == "302" || "$API_CODE" == "401" || "$API_CODE" == "403" ]]; then
                ok "API ${api_path} → $API_CODE"
            else
                err "API ${api_path} → $API_CODE"
            fi
        done
    fi

    if django_cmd "python manage.py check --deploy" >/dev/null 2>&1; then
        ok "django check --deploy → OK"
    else
        warn "django check --deploy a signalé des avertissements"
        django_cmd "python manage.py check --deploy" || true
    fi

    if [[ -f "$REPO_DIR/deploy/verify_runtime.py" ]]; then
        log "Vérification approfondie (Redis Channels, Celery, WebSocket, push)"
        VERIFY_OUTPUT=$(django_cmd "python '$REPO_DIR/deploy/verify_runtime.py' --site-url '$CHECK_URL'" 2>&1) || VERIFY_RC=$?
        VERIFY_RC=${VERIFY_RC:-0}
        echo "$VERIFY_OUTPUT"
        if [[ "$VERIFY_RC" -eq 0 ]]; then
            ok "Temps réel + notifications → OK"
        else
            err "Temps réel / notifications — échec (voir verify_runtime ci-dessus)"
            err "Vérifiez : Redis, Daphne, proxy Nginx /ws/, Firebase, utilisateur DEPLOY_VERIFY_EMAIL"
        fi
    else
        err "verify_runtime.py introuvable dans $REPO_DIR/deploy/"
    fi

    if ! $SKIP_NABOOPAY; then
        NABOO_KEY=$(grep -E '^NABOOPAY_API_KEY=' "$DJANGO_DIR/.env" 2>/dev/null | cut -d= -f2- | tr -d '\r' || true)
        if [[ -z "${NABOO_KEY// }" ]]; then
            warn "NabooPay : clé absente — skip (renseignez NABOOPAY_* ou utilisez --skip-naboopay)"
        else
            NABOO_OUTPUT=$(django_cmd "python scripts/check_naboopay_setup.py --deploy --site-url '$CHECK_URL'" 2>&1) || NABOO_RC=$?
            NABOO_RC=${NABOO_RC:-0}
            echo "$NABOO_OUTPUT"
            if [[ "$NABOO_RC" -eq 0 ]]; then
                ok "NabooPay → configuration et webhook OK"
            else
                err "NabooPay — vérification échouée"
                err "Corrigez .env / dashboard NabooPay ou relancez avec --skip-naboopay"
            fi
        fi
    fi
else
    warn "Vérifications désactivées (--no-checks)"
fi

# ── Fin ────────────────────────────────────────────────────────────────────────
echo ""
if $DEPLOY_FAILED; then
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}${BOLD}  Déploiement terminé AVEC AVERTISSEMENTS / ÉCHECS${NC}"
    echo -e "${YELLOW}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    log "Site   : $SITE_URL  (checks : $CHECK_URL)"
    log "Logs   : journalctl -u daphne-timalove -f"
    exit 1
else
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}${BOLD}  Déploiement terminé avec succès${NC}"
    echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    log "Site : $SITE_URL  (checks : $CHECK_URL)"
    log "Logs : journalctl -u daphne-timalove -f"
fi
echo ""
