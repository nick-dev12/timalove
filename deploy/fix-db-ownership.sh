#!/usr/bin/env bash
# Transfère la propriété des tables/sequences PostgreSQL à l'utilisateur Django.
# Nécessaire après pg_restore --no-owner (sinon migrate échoue : must be owner of table …).
#
# Usage (root sur le VPS) :
#   sudo bash /home/colobanes/timalove.goo-bridge.com/deploy/fix-db-ownership.sh
#   sudo bash deploy/fix-db-ownership.sh --then-deploy
#
set -euo pipefail

DB_NAME="${DB_NAME:-colobanes_timalove}"
DB_USER="${DB_USER:-colobanes_jomas}"
REPO_DIR="${REPO_DIR:-/home/colobanes/timalove.goo-bridge.com}"
THEN_DEPLOY=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --db-name)   DB_NAME="$2"; shift 2 ;;
        --db-user)   DB_USER="$2"; shift 2 ;;
        --then-deploy) THEN_DEPLOY=true; shift ;;
        -h|--help)
            echo "Usage: sudo bash deploy/fix-db-ownership.sh [--db-name NAME] [--db-user USER] [--then-deploy]"
            exit 0
            ;;
        *) echo "Option inconnue: $1" >&2; exit 1 ;;
    esac
done

if [[ "$(id -u)" -ne 0 ]]; then
    echo "À lancer en root : sudo bash deploy/fix-db-ownership.sh" >&2
    exit 1
fi

if [[ ! "$DB_USER" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "Nom d'utilisateur PostgreSQL invalide : $DB_USER" >&2
    exit 1
fi

PSQL="$(command -v psql || true)"
for b in /usr/pgsql-17/bin /usr/lib/postgresql/17/bin /usr/bin; do
    [[ -z "$PSQL" && -x "$b/psql" ]] && PSQL="$b/psql"
done
if [[ -z "$PSQL" ]]; then
    echo "psql introuvable." >&2
    exit 1
fi

echo "[fix-db] Base     : $DB_NAME"
echo "[fix-db] Propriétaire cible : $DB_USER"
echo "[fix-db] Propriétaires actuels (public) :"
sudo -u postgres "$PSQL" -d "$DB_NAME" -c \
    "SELECT tableowner, COUNT(*) FROM pg_tables WHERE schemaname = 'public' GROUP BY tableowner ORDER BY COUNT(*) DESC;"

sudo -u postgres "$PSQL" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<SQL
DO \$\$
DECLARE
    r RECORD;
    app_user text := '${DB_USER}';
BEGIN
    FOR r IN
        SELECT schemaname, tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('ALTER TABLE %I.%I OWNER TO %I', r.schemaname, r.tablename, app_user);
    END LOOP;

    FOR r IN
        SELECT sequence_schema, sequence_name
        FROM information_schema.sequences
        WHERE sequence_schema = 'public'
    LOOP
        EXECUTE format('ALTER SEQUENCE %I.%I OWNER TO %I', r.sequence_schema, r.sequence_name, app_user);
    END LOOP;
END \$\$;

GRANT ALL ON SCHEMA public TO ${DB_USER};
GRANT ALL ON ALL TABLES IN SCHEMA public TO ${DB_USER};
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
SQL

echo "[fix-db] OK — propriété transférée vers $DB_USER"

if $THEN_DEPLOY; then
    echo "[fix-db] Relance deploy.sh…"
    exec bash "$REPO_DIR/timalove/deploy.sh"
fi
