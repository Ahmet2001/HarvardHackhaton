FROM node:22-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html /app/
COPY frontend/src /app/src
ARG VITE_BIODOCKX_API_URL=http://localhost:8000
ENV VITE_BIODOCKX_API_URL=$VITE_BIODOCKX_API_URL
RUN npm install && npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
