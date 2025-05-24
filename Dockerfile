# Build stage
FROM node:18-alpine AS build

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the app
COPY . .

# Build the app (skip TypeScript check)
RUN npm run build:skip-ts

# Production stage
FROM nginx:alpine

# Copy built files from build stage to nginx serve directory
COPY --from=build /app/dist /usr/share/nginx/html

# Create nginx configuration that handles SPA routing and proxies API requests
RUN echo '\
server {\
    listen 80;\
    \
    # Frontend app\
    location / {\
        root /usr/share/nginx/html;\
        index index.html;\
        try_files $uri $uri/ /index.html;\
    }\
    \
    # Proxy API requests to Split Sentences service\
    location /api/ {\
        proxy_pass http://split_sentences:8000/api/;\
        proxy_http_version 1.1;\
        proxy_set_header Upgrade $http_upgrade;\
        proxy_set_header Connection "upgrade";\
        proxy_set_header Host $host;\
        proxy_set_header X-Real-IP $remote_addr;\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
        proxy_set_header X-Forwarded-Proto $scheme;\
        proxy_buffering off;\
    }\
}' > /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
