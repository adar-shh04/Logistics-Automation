# Stage 1: Dependencies
FROM node:18-alpine AS deps

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

# Stage 2: Development (optional target for local dev compose)
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage 3: Production Builder
FROM deps AS builder
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Stage 4: Production Web Server (Default final stage)
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
