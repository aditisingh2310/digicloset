# Use Node to build, nginx to serve
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:stable-alpine AS production
COPY --from=build /app/dist /usr/share/nginx/html
# Optional: copy custom nginx config if you want
EXPOSE 80
CMD [ "nginx", "-g", "daemon off;" ]
