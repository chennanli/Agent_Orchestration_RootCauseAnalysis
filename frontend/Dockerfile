# ==============================================================================
# TEP Frontend Dockerfile (multi-stage, builds from REPO_ROOT context)
# ==============================================================================
# Build with the REPO_ROOT as context so we can also pick up frontend/nginx.conf:
#   docker build -t tep-frontend -f frontend/Dockerfile .
#
# Stage 1: install node deps + `npm run build` to produce static `dist/`
# Stage 2: serve dist/ with nginx, using the proxy config in frontend/nginx.conf
# Final image ≈ 30 MB (nginx:alpine + the bundled JS/CSS).
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: build
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Copy only manifest files first so this layer is cached across code-only edits.
COPY frontend/package.json frontend/package-lock.json ./

# `npm ci` (clean-install) is strict: it fails if package-lock.json is out of
# sync, instead of silently regenerating. Same flag CI uses.
RUN npm ci

# Copy the rest of the frontend source.
COPY frontend/ ./

# Produces /app/dist (static HTML/JS/CSS) via `tsc && vite build`.
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: serve
# ------------------------------------------------------------------------------
FROM nginx:alpine

# Static bundle.
COPY --from=builder /app/dist /usr/share/nginx/html

# Reverse-proxy + SPA-routing config. The config inside expects the FastAPI
# backend to be reachable at `http://backend:8000` — that's the docker-compose
# service name. Outside docker-compose, set BACKEND_HOST via an
# `nginx.conf.template` if you ever need to change it.
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Quick liveness probe — nginx itself answers any path with at least a 404,
# so a 2xx from `/` is the simplest "is it serving HTML?" check.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
