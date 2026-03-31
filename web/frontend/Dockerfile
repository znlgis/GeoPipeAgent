# ── GeoPipeAgent Frontend ────────────────────────────────────────────────────
# Multi-stage: Node build → Nginx serve
# ---------------------------------------------------------------------------

# Stage 1: Build
FROM node:20-alpine AS build

WORKDIR /app

COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci

COPY web/frontend/ ./
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

COPY web/frontend/nginx.conf /etc/nginx/conf.d/geopipe.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
