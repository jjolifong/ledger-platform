# Stage 1: frontend build
FROM node:20-alpine AS build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: runtime
FROM python:3.12-slim

WORKDIR /app

COPY backend/ ./backend/
COPY --from=build /frontend/dist ./frontend/dist
COPY docker-entrypoint.sh /docker-entrypoint.sh

RUN chmod +x /docker-entrypoint.sh \
    && pip install --no-cache-dir -r backend/requirements.txt

WORKDIR /app/backend

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
