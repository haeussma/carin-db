FROM node:23-alpine

WORKDIR /app

RUN corepack enable

# Install dependencies first
COPY package.json pnpm-lock.yaml ./
RUN pnpm install

# Copy the rest of the application
COPY . .

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application in development mode
CMD ["npm", "run", "dev"]