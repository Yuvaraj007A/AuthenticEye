FROM node:18-alpine

# Install some utilities and clean up
RUN apk add --no-cache curl

WORKDIR /app

# Set node environment
ENV NODE_ENV=production

# Copy package files first for better caching
COPY package*.json ./

# Install only production dependencies
RUN npm install --omit=dev

# Copy source code
COPY . .

# Ensure upload directory exists and has correct permissions
RUN mkdir -p uploads && chown -R node:node /app

# Switch to non-root user
USER node

EXPOSE 5000

CMD ["npm", "start"]

