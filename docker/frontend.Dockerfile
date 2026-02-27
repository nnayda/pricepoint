# Build stage
FROM node:20-slim AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Production stage
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback + API reverse proxy
# Use Docker embedded DNS (127.0.0.11) and a variable so nginx resolves
# the upstream at request time instead of failing at startup.
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    client_max_body_size 0; \
    resolver 127.0.0.11 valid=30s ipv6=off; \
    location /api/ { \
        set $backend http://api:8000; \
        proxy_pass $backend; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        proxy_request_buffering off; \
    } \
    location /tiles/ { \
        set $martin http://martin:3000; \
        rewrite ^/tiles/(.*)$ /$1 break; \
        proxy_pass $martin; \
        proxy_set_header Host $host; \
        add_header Cache-Control "public, max-age=3600"; \
    } \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
