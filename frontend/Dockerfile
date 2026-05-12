# ==============================================================================
# TEP Frontend Dockerfile (Multi-Stage Build)
# ==============================================================================
# Purpose: React + TypeScript + Vite frontend
# Stage 1: Build (Node.js + dependencies) ~1.2GB
# Stage 2: Serve (Nginx + static files) ~25MB
# ==============================================================================

# Stage 1: Build the React application
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies (use npm ci for reproducible builds)
RUN npm ci

# Copy source code
COPY . .

# Build for production
RUN npm run build

# ==============================================================================
# Stage 2: Production server with Nginx
# ==============================================================================
FROM nginx:alpine

# Copy built files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]

