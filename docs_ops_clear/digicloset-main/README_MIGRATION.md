# Migration Pack — README

This folder gives you safe scripts for applying the Enterprise Upgrade Pack into any repo.

## Files
- **apply-upgrade-pack.sh**  
  Main script: applies the upgrade pack, creates backup, generates patch, creates PR.
- **rollback-upgrade-pack.sh**  
  Restores your repo from `.upgrade_backup`.
- **.gitattributes**  
  Ensures consistent text/binary handling.

---

# How to Use

### 1. Place the upgrade pack ZIP and this migration pack in the same system.

Example:
