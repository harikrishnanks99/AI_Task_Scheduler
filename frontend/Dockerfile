# ---- Stage 1: Build the React Application ----
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Build the production-ready static files
RUN npm run build

# ---- Stage 2: Serve the Application with Nginx ----
FROM nginx:1.25-alpine

# Copy the built static files from the 'builder' stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 (the default Nginx port)
EXPOSE 80

# The default Nginx command will start the server
CMD ["nginx", "-g", "daemon off;"]