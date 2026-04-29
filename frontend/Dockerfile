FROM node:18-alpine

LABEL maintainer="adar-shh04"

WORKDIR /app

COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy application files
COPY . .

EXPOSE 5173

# Start dev server with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
