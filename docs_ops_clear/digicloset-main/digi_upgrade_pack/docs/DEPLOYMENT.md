
# Full Deployment Guide (Production Ready)

## 1. Required Infrastructure
- Docker + Compose
- HTTPS reverse proxy (NGINX recommended)
- Environment variables using .env file
- Persistent PostgreSQL volume

## 2. Build & Deploy
Run:

```
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## 3. Logging
```
docker-compose logs -f backend
```

## 4. Updating
```
git pull
docker-compose build
docker-compose up -d
```
