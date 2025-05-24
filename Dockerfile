FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the app
COPY . .

# Expose port
EXPOSE 3000

# Command to run the app in development mode
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
