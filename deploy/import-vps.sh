#!/usr/bin/env bash
# Restaure le dump PostgreSQL local + les médias sur le VPS Ubuntu (mytimalove.com).
# Prérequis sur le VPS : tima.dump + timalove-media.tgz dans /tmp (ou deploy/)
#
#   sudo bash /home/jomas/timalove/deploy/import-vps.sh
#   # ou avec mot de passe explicite :
#   sudo PGPASSWORD='...' bash /home/jomas/timalove/deploy/import-vps.sh
set -euo pipefail

if [[ -f /etc/timalove/deploy.env ]]; then
    # shellcheck disable=SC1091
    source /etc/timalove/deploy.env
fi

APP_USER="${APP_USER:-jomas}"
REPO_DIR="${REPO_DIR:-/home/${APP_USER}/timalove}"
DJANGO_DIR="${DJANGO_DIR:-${REPO_DIR}/timalove}"
VENV_DIR="${VENV_DIR:-${REPO_DIR}/venv}"
DB_NAME="${DB_NAME:-timalove}"
DB_USER="${DB_USER:-timalove}"
DB_HOST="${DB_HOST:-127.0.0.1}"

# Mot de passe : env PGPASSWORD, sinon lu depuis .env
if [[ -z "${PGPASSWORD:-}" && -f "$DJANGO_DIR/.env" ]]; then
    PGPASSWORD=$(grep -E '^DB_PASSWORD=' "$DJANGO_DIR/.env" | tail -1 | cut -d= -f2- | tr -d '\r' | sed 's/^["'\'']//;s/["'\'']$//')
    export PGPASSWORD
fi
if [[ -z "${PGPASSWORD:-}" ]]; then
    echo "Définissez PGPASSWORD ou DB_PASSWORD dans $DJANGO_DIR/.env" >&2
    exit 1
fi
export PGPASSWORD

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DUMP=""
MEDIA_TGZ=""
for cand in /tmp "$SCRIPT_DIR" "$REPO_DIR/migrate-vps" "$DJANGO_DIR"; do
    [[ -f "$cand/tima.dump" && -z "$DUMP" ]] && DUMP="$cand/tima.dump"
    [[ -f "$cand/timalove-media.tgz" && -z "$MEDIA_TGZ" ]] && MEDIA_TGZ="$cand/timalove-media.tgz"
done

if [[ "$(id -u)" -ne 0 ]]; then
    echo "À lancer en root : sudo bash import-vps.sh" >&2
    exit 1
fi
if [[ -z "$DUMP" ]]; then
    echo "tima.dump introuvable (cherché dans /tmp, deploy/, migrate-vps/)." >&2
    exit 1
fi
if [[ -z "$MEDIA_TGZ" ]]; then
    echo "timalove-media.tgz introuvable." >&2
    exit 1
fi

echo "[import] Dump   : $DUMP ($(du -h "$DUMP" | awk '{print $1}'))"
echo "[import] Médias : $MEDIA_TGZ ($(du -h "$MEDIA_TGZ" | awk '{print $1}'))"
echo "[import] DB     : $DB_NAME / $DB_USER"

echo "[import] Arrêt des services Django…"
systemctl stop daphne-timalove celery-timalove celerybeat-timalove || true

PG_RESTORE="$(command -v pg_restore || true)"
PSQL="$(command -v psql || true)"
for b in /usr/lib/postgresql/*/bin /usr/bin; do
    [[ -z "$PG_RESTORE" && -x "$b/pg_restore" ]] && PG_RESTORE="$b/pg_restore"
    [[ -z "$PSQL" && -x "$b/psql" ]] && PSQL="$b/psql"
done
if [[ -z "$PG_RESTORE" || -z "$PSQL" ]]; then
    echo "pg_restore / psql introuvable." >&2
    exit 1
fi

echo "[import] Restauration PostgreSQL → $DB_NAME…"
sudo -u postgres "$PSQL" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
    >/dev/null || true

RESTORE_OK=0
if sudo -u postgres "$PG_RESTORE" --clean --if-exists --no-owner --no-acl -d "$DB_NAME" "$DUMP"; then
    RESTORE_OK=1
elif "$PG_RESTORE" -h "$DB_HOST" -U "$DB_USER" --clean --if-exists --no-owner --no-acl -d "$DB_NAME" "$DUMP"; then
    RESTORE_OK=1
fi
if [[ "$RESTORE_OK" -ne 1 ]]; then
    echo "[import] Échec pg_restore" >&2
    systemctl start daphne-timalove celery-timalove celerybeat-timalove || true
    exit 1
fi

sudo -u postgres "$PSQL" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL || true
GRANT ALL ON SCHEMA public TO $DB_USER;
GRANT ALL ON ALL TABLES IN SCHEMA public TO $DB_USER;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $DB_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $DB_USER;
SQL

if [[ -f "$SCRIPT_DIR/fix-db-ownership.sh" ]]; then
    echo "[import] Propriété des tables → $DB_USER…"
    DB_NAME="$DB_NAME" DB_USER="$DB_USER" bash "$SCRIPT_DIR/fix-db-ownership.sh" || true
fi

echo "[import] Réécriture des URLs photos CDN → /media/…"
"$PSQL" -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL' || true
UPDATE core_profile
SET photo_url = '/media/profile-photos/' || regexp_replace(split_part(photo_url, '?', 1), '^.*/', '')
WHERE photo_url LIKE 'https://media.mytimalove.com/%'
   OR photo_url LIKE 'http://media.mytimalove.com/%';

UPDATE core_profile
SET photo_url_2 = '/media/profile-photos/' || regexp_replace(split_part(photo_url_2, '?', 1), '^.*/', '')
WHERE photo_url_2 LIKE 'https://media.mytimalove.com/%'
   OR photo_url_2 LIKE 'http://media.mytimalove.com/%';

UPDATE core_profile
SET photo_url_3 = '/media/profile-photos/' || regexp_replace(split_part(photo_url_3, '?', 1), '^.*/', '')
WHERE photo_url_3 LIKE 'https://media.mytimalove.com/%'
   OR photo_url_3 LIKE 'http://media.mytimalove.com/%';

UPDATE core_profile
SET verification_photo_url = '/media/profile-photos/' || regexp_replace(split_part(verification_photo_url, '?', 1), '^.*/', '')
WHERE verification_photo_url LIKE 'https://media.mytimalove.com/%'
   OR verification_photo_url LIKE 'http://media.mytimalove.com/%';

UPDATE core_profilegalleryphoto
SET photo_url = '/media/profile-photos/' || regexp_replace(split_part(photo_url, '?', 1), '^.*/', '')
WHERE photo_url LIKE 'https://media.mytimalove.com/%'
   OR photo_url LIKE 'http://media.mytimalove.com/%';

UPDATE core_message
SET voice_url = '/media/voice-messages/' || regexp_replace(split_part(voice_url, '?', 1), '^.*/', '')
WHERE voice_url LIKE 'https://media.mytimalove.com/%'
   OR voice_url LIKE 'http://media.mytimalove.com/%'
   OR voice_url LIKE 'https://%.supabase.co/%';
SQL

echo "[import] Extraction des médias…"
mkdir -p "$DJANGO_DIR"
tar -xzf "$MEDIA_TGZ" -C "$DJANGO_DIR"
chown -R "$APP_USER:$APP_USER" "$DJANGO_DIR/media"
find "$DJANGO_DIR/media" -type d -exec chmod 775 {} \;
find "$DJANGO_DIR/media" -type f -exec chmod 664 {} \;
chmod 755 "/home/$APP_USER" 2>/dev/null || true
chmod -R o+rX "$DJANGO_DIR/media" 2>/dev/null || true

echo "[import] Migrations…"
sudo -u "$APP_USER" bash -lc \
    "cd '$DJANGO_DIR' && source '$VENV_DIR/bin/activate' && python manage.py migrate --noinput"

echo "[import] Redémarrage des services…"
systemctl start daphne-timalove celery-timalove celerybeat-timalove
sleep 2
systemctl is-active daphne-timalove celery-timalove celerybeat-timalove

"$PSQL" -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT (SELECT COUNT(*) FROM auth_user) AS users, (SELECT COUNT(*) FROM core_profile) AS profiles, (SELECT COUNT(*) FROM core_message) AS messages;"

echo ""
echo "[OK] Import terminé."
echo "     http://149.56.140.166/connexion/"
echo "     (ou https://mytimalove.com après DNS)"
