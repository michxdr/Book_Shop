#!/bin/bash
# Migrate data from SQLite to PostgreSQL.
#
# Prerequisites:
#   - Python environment with Django + psycopg2 installed
#   - Docker containers running: docker compose up -d db redis
#   - db.sqlite3 exists in the project root
#
# Usage:
#   bash migrate_sqlite_to_postgres.sh

set -e

DUMP_FILE="sqlite_dump.json"

if [ ! -f "db.sqlite3" ]; then
    echo "ERROR: db.sqlite3 not found. Nothing to migrate."
    exit 1
fi

echo "==> [1/4] Dumping data from SQLite..."
python manage.py dumpdata \
    --settings=book_shop.settings_sqlite \
    --natural-foreign \
    --natural-primary \
    --exclude=contenttypes \
    --exclude=auth.permission \
    --indent=2 \
    -o "$DUMP_FILE"
echo "    Saved to $DUMP_FILE"

echo "==> [2/4] Waiting for PostgreSQL..."
until docker compose exec -T db pg_isready \
    -U "${DB_USER:-book_shop_user}" \
    -d "${DB_NAME:-book_shop}" 2>/dev/null; do
    sleep 1
done
echo "    PostgreSQL is ready!"

echo "==> [3/4] Running migrations on PostgreSQL..."
docker compose exec -T web python manage.py migrate --noinput

echo "==> [4/4] Loading data into PostgreSQL..."
docker compose cp "$DUMP_FILE" web:/app/"$DUMP_FILE"
docker compose exec -T web python manage.py loaddata "$DUMP_FILE" \
    --exclude=contenttypes \
    --exclude=auth.permission

echo "==> Cleanup..."
rm -f "$DUMP_FILE"
docker compose exec -T web rm -f /app/"$DUMP_FILE"

echo ""
echo "==> Migration complete! All data moved from SQLite to PostgreSQL."
