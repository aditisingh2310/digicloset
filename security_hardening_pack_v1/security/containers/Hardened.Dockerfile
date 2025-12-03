# Example hardened Dockerfile (multi-stage, minimal privileges)
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --production=false
COPY . .
RUN npm run build

FROM node:18-alpine AS runtime
WORKDIR /app
# create non-root user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
COPY --from=build /app/dist ./dist
COPY package*.json ./
RUN npm ci --production=true --ignore-scripts
USER appuser
EXPOSE 3000
CMD ["node", "dist/index.js"]
