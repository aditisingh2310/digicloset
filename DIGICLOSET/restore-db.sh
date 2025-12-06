#!/bin/bash
# restore-db.sh - Restore Supabase DB from a backup file

set -e

if [ -z "$1" ]; then
  echo "Usage: ./restore-db.sh <backup_file.sql>"
  exit 1
fi

BACKUP_FILE=$1

echo "Restoring database from $BACKUP_FILE ..."

PGHOST=$(kubectl get secret supabase-db-credentials -o jsonpath='{.data.host}' | base64 -d)
PGUSER=$(kubectl get secret supabase-db-credentials -o jsonpath='{.data.user}' | base64 -d)
PGPASSWORD=$(kubectl get secret supabase-db-credentials -o jsonpath='{.data.password}' | base64 -d)
PGDATABASE=$(kubectl get secret supabase-db-credentials -o jsonpath='{.data.database}' | base64 -d)

export PGPASSWORD=$PGPASSWORD
pg_restore -h $PGHOST -U $PGUSER -d $PGDATABASE $BACKUP_FILE

echo "✅ Database restored successfully."