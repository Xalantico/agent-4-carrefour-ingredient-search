#!/bin/bash

# Lexia Menu Food Agent - Deployment Script
# This script helps deploy the agent using Docker

set -e

echo "🚀 Deploying Lexia Menu Food Agent..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t menufood-agent .

# Stop existing container if running
echo "🛑 Stopping existing container..."
docker-compose down 2>/dev/null || true

# Start the service
echo "🏃 Starting service..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for service to be healthy..."
sleep 10

# Check if service is running
if curl -f http://localhost:8002/api/v1/health > /dev/null 2>&1; then
    echo "✅ Service is running successfully!"
    echo "🌐 API available at: http://localhost:8002"
    echo "📚 API docs at: http://localhost:8002/docs"
    echo "🔍 Health check: http://localhost:8002/api/v1/health"
else
    echo "❌ Service failed to start. Check logs with: docker-compose logs"
    exit 1
fi

echo "🎉 Deployment complete!"
