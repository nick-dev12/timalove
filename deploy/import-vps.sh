#!/usr/bin/env bash
# Restaure le dump PostgreSQL local + les médias sur le VPS.
# Prérequis : tima.dump et timalove-media.tgz dans le même dossier que ce script
#   (ou dans /home/colobanes/timalove.goo-bridge.com/migrate-vps/)
#
#   sudo bash import-vps.sh
set -euo pipefail

APP_USER="${APP_USER:-colobanes}"
DJANGO_DIR="${DJANGO_DIR:-/home/colobanes/timalove.goo-bridge.com/timalove}"
DB_NAME="${DB_NAME:-colobanes_timalove}"
DB_USER="${DB_USER:-colobanes_jomas}"
DB_HOST="${DB_HOST:-127.0.0.1}"
if [[ -z "${PGPASSWORD:-}" ]]; then
    echo "Définissez PGPASSWORD (mot de passe PostgreSQL Webuzo), par ex. :" >&2
    echo "  sudo PGPASSWORD='votre-mdp' bash import-vps.sh" >&2
    exit 1
fi
export PGPASSWORD

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DUMP=""
MEDIA_TGZ=""
for cand in "$SCRIPT_DIR" /home/colobanes/timalove.goo-bridge.com/migrate-vps /tmp; do
    [[ -f "$cand/tima.dump" && -z "$DUMP" ]] && DUMP="$cand/tima.dump"
    [[ -f "$cand/timalove-media.tgz" && -z "$MEDIA_TGZ" ]] && MEDIA_TGZ="$cand/timalove-media.tgz"
done

if [[ "$(id -u)" -ne 0 ]]; then
    echo "À lancer en root : sudo bash import-vps.sh" >&2
    exit 1
fi
if [[ -z "$DUMP" ]]; then
    echo "tima.dump introuvable." >&2
    exit 1
fi
if [[ -z "$MEDIA_TGZ" ]]; then
    echo "timalove-media.tgz introuvable." >&2
    exit 1
fi

echo "[import] Dump   : $DUMP"
echo "[import] Médias : $MEDIA_TGZ"

echo "[import] Arrêt des services Django (connexions DB)…"
systemctl stop daphne-timalove celery-timalove celerybeat-timalove

PG_RESTORE="$(command -v pg_restore || true)"
PSQL="$(command -v psql || true)"
for b in /usr/pgsql-17/bin /usr/lib/postgresql/17/bin /usr/bin; do
    [[ -z "$PG_RESTORE" && -x "$b/pg_restore" ]] && PG_RESTORE="$b/pg_restore"
    [[ -z "$PSQL" && -x "$b/psql" ]] && PSQL="$b/psql"
done
if [[ -z "$PG_RESTORE" || -z "$PSQL" ]]; then
    echo "pg_restore / psql introuvable." >&2
    exit 1
fi

echo "[import] Restauration PostgreSQL → $DB_NAME…"
"$PSQL" -h "$DB_HOST" -U "$DB_USER" -d postgres -c \
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

echo "[import] Propriété des tables → $DB_USER (requis pour migrate)…"
DB_NAME="$DB_NAME" DB_USER="$DB_USER" bash "$SCRIPT_DIR/fix-db-ownership.sh"

echo "[import] Réécriture des URLs photos CDN → /media/…"
"$PSQL" -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
UPDATE core_profile
SET photo_url = '/media/profile-photos/' || regexp_replace(split_part(photo_url, '?', 1), '^.*/', '')
WHERE photo_url LIKE 'https://media.mytimalove.com/%';

UPDATE core_profile
SET photo_url_2 = '/media/profile-photos/' || regexp_replace(split_part(photo_url_2, '?', 1), '^.*/', '')
WHERE photo_url_2 LIKE 'https://media.mytimalove.com/%';

UPDATE core_profile
SET photo_url_3 = '/media/profile-photos/' || regexp_replace(split_part(photo_url_3, '?', 1), '^.*/', '')
WHERE photo_url_3 LIKE 'https://media.mytimalove.com/%';

UPDATE core_profile
SET verification_photo_url = '/media/profile-photos/' || regexp_replace(split_part(verification_photo_url, '?', 1), '^.*/', '')
WHERE verification_photo_url LIKE 'https://media.mytimalove.com/%';

UPDATE core_profilegalleryphoto
SET photo_url = '/media/profile-photos/' || regexp_replace(split_part(photo_url, '?', 1), '^.*/', '')
WHERE photo_url LIKE 'https://media.mytimalove.com/%';

UPDATE core_message
SET voice_url = '/media/voice-messages/' || regexp_replace(split_part(voice_url, '?', 1), '^.*/', '')
WHERE voice_url LIKE 'https://media.mytimalove.com/%'
   OR voice_url LIKE 'https://%.supabase.co/%';
SQL

echo "[import] Extraction des médias…"
mkdir -p "$DJANGO_DIR"
tar -xzf "$MEDIA_TGZ" -C "$DJANGO_DIR"
chown -R "$APP_USER:$APP_USER" "$DJANGO_DIR/media"
find "$DJANGO_DIR/media" -type d -exec chmod 775 {} \;
find "$DJANGO_DIR/media" -type f -exec chmod 664 {} \;

echo "[import] Migrations (au cas où)…"
sudo -u "$APP_USER" bash -lc \
    "cd '$DJANGO_DIR' && source '../venv/bin/activate' && python manage.py migrate --noinput"

echo "[import] Redémarrage des services…"
systemctl start daphne-timalove celery-timalove celerybeat-timalove
sleep 2
systemctl is-active daphne-timalove celery-timalove celerybeat-timalove

"$PSQL" -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT (SELECT COUNT(*) FROM auth_user) AS users, (SELECT COUNT(*) FROM core_profile) AS profiles, (SELECT COUNT(*) FROM core_message) AS messages;"

echo ""
echo "[OK] Import terminé. Les utilisateurs se connectent avec leur email / mot de passe local."
echo "     https://timalove.goo-bridge.com/connexion/"
