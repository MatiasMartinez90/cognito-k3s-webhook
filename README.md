# Cognito K3s Webhook

FastAPI microservice for handling AWS Cognito PostConfirmation events, designed to replace Lambda functions and run on Kubernetes (K3s) cluster.

## 🎯 Purpose

This microservice replaces the AWS Lambda PostConfirmation trigger with a cost-effective webhook solution running on your K3s cluster. It handles user registration events from Cognito and creates user records in your PostgreSQL database.

## 🏗️ Architecture

```
Cognito → HTTP Webhook → FastAPI Microservice (K3s) → PostgreSQL (K3s)
```

**Benefits:**
- ✅ No NAT Gateway costs (~$30/month saved)
- ✅ No Lambda costs
- ✅ Direct internal access to PostgreSQL
- ✅ Full control over the code and deployment
- ✅ Better observability and logging

## 🚀 Features

- **FastAPI** with async support
- **PostgreSQL** integration with psycopg2
- **Health checks** for monitoring
- **Test endpoints** for debugging
- **Security** with non-root container user
- **Kubernetes manifests** ready for deployment

## 📋 Endpoints

- `GET /` - Service status
- `GET /health` - Health check with database connectivity test
- `POST /cognito-webhook` - Main Cognito PostConfirmation handler
- `POST /test-webhook` - Test endpoint for development

## 🛠️ Quick Start

### 1. Build and Push Docker Image

```bash
# Build and push to private registry
./docker-build.sh

# Or with specific tag
./docker-build.sh v1.0.0
```

### 2. Deploy to K3s

```bash
# Apply all manifests (in order)
kubectl apply -f k8s/01-namespace.yaml
kubectl apply -f k8s/02-secret.yaml
kubectl apply -f k8s/03-configmap.yaml
kubectl apply -f k8s/04-deployment.yaml
kubectl apply -f k8s/05-service.yaml
kubectl apply -f k8s/06-ingress.yaml

# Or apply all at once
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n rrhh-agent
kubectl get svc -n rrhh-agent
kubectl get ingress -n rrhh-agent
```

### 3. Test the Service

```bash
# Health check via ingress
curl https://webhook-rrhh.cloud-it.com.ar/health

# Test webhook endpoint
curl -X POST https://webhook-rrhh.cloud-it.com.ar/test-webhook

# Check SSL certificate
curl -vI https://webhook-rrhh.cloud-it.com.ar/health
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `postgresql-service.postgresql.svc.cluster.local` | PostgreSQL hostname |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `agent` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `password` | Database password (from secret) |
| `PORT` | `8000` | Service port |
| `LOG_LEVEL` | `info` | Logging level |

### Kubernetes Resources

- **Namespace**: `rrhh-agent`
- **Registry**: `registry.cloud-it.com.ar/cognito-k3s-webhook:latest`
- **Service Type**: `ClusterIP` (accessed via Ingress)
- **Ingress Domain**: `webhook-rrhh.cloud-it.com.ar`
- **Replicas**: 2 (for high availability)
- **Resource Limits**: 256Mi memory, 200m CPU
- **TLS Certificate**: Automated via cert-manager + Let's Encrypt

## 🔌 Cognito Configuration

To configure Cognito to use this webhook instead of Lambda:

1. **Remove Lambda trigger** from Cognito User Pool (`us-east-1_MeClCiUAC`)
2. **Configure HTTP webhook** endpoint:
   ```
   URL: https://webhook-rrhh.cloud-it.com.ar/cognito-webhook
   Method: POST
   Content-Type: application/json
   ```

### AWS CLI Configuration Commands

```bash
# Remove existing Lambda trigger
aws cognito-idp update-user-pool \
  --user-pool-id us-east-1_MeClCiUAC \
  --lambda-config '{}'

# Note: Cognito doesn't directly support HTTP webhooks for PostConfirmation
# Alternative approaches:
# 1. Keep Lambda but make it call the webhook
# 2. Use EventBridge + API Gateway integration
# 3. Implement custom authentication flow
```

## 🗄️ Database Schema

The service expects these tables in PostgreSQL:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cognito_user_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    picture_url TEXT,
    provider VARCHAR(50) DEFAULT 'google',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    onboarding_completed BOOLEAN DEFAULT false,
    preferences JSONB DEFAULT '{}'::jsonb
);
```

## 🔒 Security

- Non-root container user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- Resource limits enforced
- Health checks for reliability

## 📊 Monitoring

- **Liveness probe**: `/health` endpoint
- **Readiness probe**: `/health` endpoint with DB connectivity check
- **Logs**: Structured logging with request/response details

## 🐛 Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n rrhh-agent
kubectl describe pod <pod-name> -n rrhh-agent
```

### View Logs
```bash
kubectl logs -f deployment/cognito-webhook -n rrhh-agent
```

### Test Database Connection
```bash
kubectl exec -it deployment/cognito-webhook -n rrhh-agent -- curl http://localhost:8000/health
```

### Manual Test
```bash
curl -X POST https://webhook-rrhh.cloud-it.com.ar/test-webhook
```

### Check Ingress and Certificate
```bash
kubectl get ingress -n rrhh-agent
kubectl describe ingress cognito-webhook-ingress -n rrhh-agent
kubectl get certificate -n rrhh-agent
```

## 📝 Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (for external DB access)
export DB_HOST=44.217.173.244
export DB_PORT=32027
export DB_PASSWORD=password

# Run locally
python app.py
```

### Docker Development

```bash
# Build image locally
docker build -t cognito-k3s-webhook:dev .

# Run container locally
docker run -p 8000:8000 \
  -e DB_HOST=postgresql-service.postgresql.svc.cluster.local \
  -e DB_PORT=5432 \
  -e DB_PASSWORD=password \
  cognito-k3s-webhook:dev
```

### Registry Management

```bash
# Login to private registry
echo "Secure@2025!" | docker login registry.cloud-it.com.ar --username admin --password-stdin

# Manual push
docker tag cognito-k3s-webhook:latest registry.cloud-it.com.ar/cognito-k3s-webhook:latest
docker push registry.cloud-it.com.ar/cognito-k3s-webhook:latest

# View registry contents
curl -u admin:Secure@2025! https://registry.cloud-it.com.ar/v2/_catalog
```

## 🎯 Deployment Steps

1. **Build and push image**
   ```bash
   ./docker-build.sh
   ```

2. **Deploy to K3s cluster**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Verify deployment**
   ```bash
   kubectl get pods -n rrhh-agent
   curl https://webhook-rrhh.cloud-it.com.ar/health
   ```

4. **Configure Cognito integration** (see Cognito Configuration section)

5. **Test complete flow**
   ```bash
   curl -X POST https://webhook-rrhh.cloud-it.com.ar/test-webhook
   ```

## 📂 Project Structure

```
cognito-k3s-webhook/
├── app.py                    # Main FastAPI application
├── requirements.txt          # Python dependencies
├── Dockerfile               # Docker container definition
├── docker-build.sh         # Build and push script
├── README.md               # This documentation
└── k8s/                    # Kubernetes manifests
    ├── 01-namespace.yaml   # rrhh-agent namespace
    ├── 02-secret.yaml      # DB password + registry credentials
    ├── 03-configmap.yaml   # Environment configuration
    ├── 04-deployment.yaml  # Application deployment
    ├── 05-service.yaml     # ClusterIP service
    └── 06-ingress.yaml     # Traefik ingress with TLS
```

## 🚀 Migration from Lambda

This project replaces the original AWS Lambda PostConfirmation function with benefits:

- ✅ **Cost Savings**: No NAT Gateway (~$30/month) or Lambda execution costs
- ✅ **Direct Database Access**: Internal cluster connectivity to PostgreSQL
- ✅ **Better Observability**: Full control over logging and monitoring  
- ✅ **Simplified Architecture**: No VPC complexity or Lambda cold starts
- ✅ **SSL/TLS**: Automatic certificate management via cert-manager

## 📖 Related Resources

- **Original Lambda**: `PostConfirmationFn-agent` in AWS Lambda console
- **Database**: PostgreSQL in `postgresql` namespace of K3s cluster  
- **Cognito Pool**: `us-east-1_MeClCiUAC` user pool
- **Domain**: `webhook-rrhh.cloud-it.com.ar` (managed by Traefik + cert-manager)
- **Registry**: `registry.cloud-it.com.ar` private Docker registry
