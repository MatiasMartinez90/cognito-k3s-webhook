#!/bin/bash

# Build and Deploy script for Cognito K3s Webhook
# Builds Docker image and pushes to private registry

set -e

REGISTRY="registry.cloud-it.com.ar"
IMAGE_NAME="cognito-k3s-webhook"
TAG="${1:-latest}"
FULL_IMAGE="${REGISTRY}/${IMAGE_NAME}:${TAG}"

echo "🔨 Building Docker image: ${FULL_IMAGE}"

# Build the image
docker build -t ${IMAGE_NAME}:${TAG} .
docker tag ${IMAGE_NAME}:${TAG} ${FULL_IMAGE}

echo "✅ Docker image built successfully!"

# Login to registry
echo "🔐 Logging into registry..."
echo "Secure@2025!" | docker login ${REGISTRY} --username admin --password-stdin

# Push to registry
echo "📤 Pushing image to registry..."
docker push ${FULL_IMAGE}

echo "✅ Image pushed successfully!"

# Cleanup local tag
docker rmi ${FULL_IMAGE} || true
docker rmi ${IMAGE_NAME}:${TAG} || true

echo ""
echo "🚀 Ready to deploy!"
echo ""
echo "Next steps:"
echo "1. Apply manifests: kubectl apply -f k8s/"
echo "2. Check deployment: kubectl get pods -n rrhh-agent"
echo "3. Check ingress: kubectl get ingress -n rrhh-agent"
echo "4. Test webhook: curl https://webhook-rrhh.cloud-it.com.ar/health"