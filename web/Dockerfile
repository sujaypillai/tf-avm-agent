# ── Stage 1: build ───────────────────────────────────────────────────────────
FROM node:22-alpine AS build

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
# VITE_API_URL is intentionally left empty at build time; nginx proxies /api/
# at runtime so the browser never needs an absolute backend URL.
RUN npm run build

# ── Stage 2: serve ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS serve

# Install envsubst (part of gettext) for runtime env-var substitution in nginx config
RUN apk add --no-cache gettext

# Copy custom nginx template (uses $BACKEND_URL env var)
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built assets from the build stage
COPY --from=build /app/dist /usr/share/nginx/html

# nginx image already exposes port 80; make it explicit
EXPOSE 80

# Use envsubst to render the nginx config at container start, then launch nginx
CMD ["/bin/sh", "-c", \
     "envsubst '${BACKEND_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
