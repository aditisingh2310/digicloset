# README_BACKUP.md

## Overview
This pack adds **Backup, Disaster Recovery, and Data Retention** to Digicloset using Supabase Storage.

### Components
- `supabase-backup.yaml`: Automates daily DB backups to Supabase Storage.
- `objectstore-backup.yaml`: Mirrors Supabase file storage daily.
- `restore-db.sh`: Restore script for Supabase database.
- `retention-policy.yaml`: Prunes old backups (default: keep 30 days).

### Setup
1. Create Supabase secrets:
```bash
kubectl create secret generic supabase-db-credentials   --from-literal=host=<db_host>   --from-literal=user=<db_user>   --from-literal=password=<db_pass>   --from-literal=database=<db_name>

kubectl create secret generic supabase-api-key   --from-literal=key=<your_supabase_service_role_key>
```

2. Apply all YAMLs:
```bash
kubectl apply -f infra/backup/
```

3. To restore:
```bash
chmod +x infra/backup/restore-db.sh
./infra/backup/restore-db.sh path_to_backup.sql
```

### Verification
- Backups appear under your Supabase Storage bucket (`digicloset-backups`).
- CronJobs log success messages in Kubernetes logs.
- Old backups are cleaned automatically every 30 days.

---
✅ *This pack ensures your Digicloset data is safe, recoverable, and compliant with enterprise DR standards.*