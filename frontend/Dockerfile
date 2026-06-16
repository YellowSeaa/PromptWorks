FROM --platform=$BUILDPLATFORM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
COPY index.html ./
COPY tsconfig.json vite.config.ts ./
COPY src ./src
COPY public ./public

ARG VITE_API_BASE_URL="/api/v1"
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm ci && npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
