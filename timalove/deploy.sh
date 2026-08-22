#!/usr/bin/env bash
# =============================================================================
# TIMALOVE — Script de déploiement VPS (Webuzo)
# Usage (en root sur le VPS) :
#   sudo bash /home/colobanes/timalove.goo-bridge.com/timalove/deploy.sh
#   sudo bash timalove/deploy.sh --fast          # CSS/JS seulement
#   sudo bash timalove/deploy.sh --skip-pip      # sans pip install
#
# Premier install : lancer d'abord deploy/bootstrap.sh
# =============================================================================

set -euo pipefail

# ── Configuration (adapter si besoin) ────────────────────────────────────────
APP_USER="${APP_USER:-colobanes}"
REPO_DIR="${REPO_DIR:-/home/colobanes/timalove.goo-bridge.com}"
DJANGO_DIR="${DJANGO_DIR:-${REPO_DIR}/timalove}"
VENV_DIR="${VENV_DIR:-${REPO_DIR}/venv}"
GIT_BRANCH="${GIT_BRANCH:-main}"
SITE_URL="${SITE_URL:-https://timalove.goo-bridge.com}"
SETTINGS_FILE="timalove/config/settings.py"

SERVICES=(
    "daphne-timalove"
    "celery-timalove"
    "celerybeat-timalove"
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

usage() {
    cat <<'EOF'
Usage: deploy.sh [OPTIONS]

Déploie la dernière version depuis GitHub et redémarre les services.

Options:
  --fast              Déploiement rapide : git pull + collectstatic uniquement
  --skip-pip          Ne pas exécuter pip install
  --skip-migrate      Ne pas exécuter migrate
  --skip-static       Ne pas exécuter collectstatic
  --skip-restart      Ne pas redémarrer Daphne/Celery
  --skip-git          Ne pas faire git pull (migrate/static/restart seulement)
  --reset-settings    Abandonner les modifs locales de settings.py avant pull
  --no-checks         Pas de vérifications finales (curl, celery ping)
  -h, --help          Afficher cette aide

Exemples:
  sudo bash timalove/deploy.sh
  sudo bash timalove/deploy.sh --fast
  sudo bash timalove/deploy.sh --reset-settings
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
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
err()  { echo -e "${RED}[ERREUR]${NC} $*" >&2; }

# ── Vérifications préalables ───────────────────────────────────────────────────
if [[ "$(id -u)" -ne 0 ]]; then
    err "Ce script doit être exécuté en root (ou via sudo)."
    err "Exemple : sudo bash timalove/deploy.sh"
    exit 1
fi

if ! id "$APP_USER" &>/dev/null; then
    err "Utilisateur introuvable : $APP_USER"
    exit 1
fi

if [[ ! -d "$REPO_DIR/.git" ]]; then
    err "Dépôt Git introuvable : $REPO_DIR"
    err "Lancez d'abord : sudo bash deploy/bootstrap.sh"
    exit 1
fi

if [[ ! -f "$DJANGO_DIR/manage.py" ]]; then
    err "Projet Django introuvable : $DJANGO_DIR/manage.py"
    exit 1
fi

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    err "Virtualenv introuvable : $VENV_DIR"
    err "Lancez d'abord : sudo bash deploy/bootstrap.sh"
    exit 1
fi

if [[ ! -f "$DJANGO_DIR/.env" ]]; then
    err "Fichier .env manquant : $DJANGO_DIR/.env"
    err "Copiez deploy/env.production.example vers timalove/.env et remplissez les secrets."
    exit 1
fi

run_as_app() {
    sudo -u "$APP_USER" bash -lc "$1"
}

django_cmd() {
    run_as_app "cd '$DJANGO_DIR' && source '$VENV_DIR/bin/activate' && $1"
}

# Retire les fichiers non suivis qui bloquent git pull (copiés à la main sur le VPS).
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
if $FAST_MODE; then warn "Mode rapide (--fast) : static uniquement, pas de restart"; fi
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
    run_as_app "cd '$REPO_DIR' && git fetch origin && git pull origin '$GIT_BRANCH'"
    ok "Code à jour ($(run_as_app "cd '$REPO_DIR' && git rev-parse --short HEAD"))"
else
    log "Étape 1/5 — Git pull (ignoré)"
fi

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
    ok "Fichiers statiques publiés"
else
    log "Étape 4/5 — collectstatic (ignoré)"
fi

# ── 5. Redémarrage services ────────────────────────────────────────────────────
if ! $SKIP_RESTART; then
    log "Étape 5/5 — Redémarrage services systemd"
    for svc in "${SERVICES[@]}"; do
        if systemctl list-unit-files --type=service --no-legend 2>/dev/null | grep -q "^${svc}.service"; then
            systemctl restart "$svc"
            ok "Redémarré : $svc"
        else
            warn "Service non installé (ignoré) : $svc"
            warn "Lancez : sudo bash $REPO_DIR/deploy/bootstrap.sh"
        fi
    done
    sleep 2
else
    log "Étape 5/5 — Redémarrage services (ignoré)"
fi

# ── Vérifications finales ──────────────────────────────────────────────────────
echo ""
log "Vérifications finales"
echo ""

if ! $SKIP_RESTART; then
    for svc in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            ok "$svc → active (running)"
        elif systemctl list-unit-files --type=service --no-legend 2>/dev/null | grep -q "^${svc}.service"; then
            err "$svc → inactif ou en erreur"
            systemctl status "$svc" --no-pager -l || true
        fi
    done
fi

if $RUN_CHECKS; then
    if command -v curl &>/dev/null; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$SITE_URL/" || echo "000")
        if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "301" || "$HTTP_CODE" == "302" || "$HTTP_CODE" == "405" ]]; then
            ok "Site HTTP → $HTTP_CODE ($SITE_URL)"
        else
            warn "Site HTTP → $HTTP_CODE (attendu 200, 301, 302 ou 405)"
        fi
    fi

    if ! $SKIP_RESTART && ! $FAST_MODE; then
        if django_cmd "python manage.py check --deploy" >/dev/null 2>&1; then
            ok "django check --deploy → OK"
        else
            warn "django check --deploy a signalé des avertissements (voir : python manage.py check --deploy)"
        fi

        if django_cmd "celery -A config inspect ping --timeout 5" >/dev/null 2>&1; then
            ok "Celery worker → répond au ping"
        else
            warn "Celery ping a échoué (voir : journalctl -u celery-timalove -n 50)"
        fi

        VERIFY_OUTPUT=$(django_cmd "python '$REPO_DIR/deploy/verify_runtime.py' --site-url '$SITE_URL'" 2>&1) || VERIFY_RC=$?
        VERIFY_RC=${VERIFY_RC:-0}
        echo "$VERIFY_OUTPUT"
        if [[ "$VERIFY_RC" -eq 0 ]]; then
            ok "Notifications + WebSocket → OK"
        else
            warn "Vérifications notifications/WebSocket incomplètes (voir ci-dessus)"
        fi
    fi
fi

# ── Fin ────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Déploiement terminé avec succès${NC}"
echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════════════════${NC}"
echo ""
log "Site : $SITE_URL"
log "Logs : journalctl -u daphne-timalove -f"
echo ""
