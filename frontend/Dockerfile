FROM node:18-alpine

WORKDIR /app

# Install dependencies first
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the application
COPY . .

# Build the application
RUN npm run build

# Expose the port the app runs on
EXPOSE 3000

# Command to run the application
CMD ["npm", "start"] 