# Database migrations
This folder should contain your migration scripts and a README explaining which tool you use (Prisma, Flyway, Alembic, Liquibase, etc.).

Recommended pattern:
- Use a directory per tool (e.g. prisma/, alembic/)
- Commit migration files to git
- Provide `infra/migrate.sh` to run them
