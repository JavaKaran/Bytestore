FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json* ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Set environment variable
ENV NEXT_TELEMETRY_DISABLED=1

# Run the development server (bind to 0.0.0.0 for Docker)
CMD ["npx", "next", "dev", "-H", "0.0.0.0"]
