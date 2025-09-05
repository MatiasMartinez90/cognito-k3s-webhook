# 🚀 Deployment Guide

## GitHub Actions CI/CD Pipeline

This project uses GitHub Actions for CI/CD with ArgoCD for GitOps deployment.

## 🔧 Required GitHub Secrets

Configure these secrets in your GitHub repository settings:

### Registry Access
- **Name**: `REGISTRY_PASSWORD`
- **Value**: `Secure@2025!`
- **Description**: Password for private Docker registry `registry.cloud-it.com.ar`

### Setting up Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the required secret:

```
Name: REGISTRY_PASSWORD
Value: Secure@2025!
```

## 🔄 Pipeline Workflow

The CI/CD pipeline consists of 3 main jobs:

### 1. Build and Push (`build-and-push`)
- ✅ Builds Docker image for multiple architectures (linux/amd64, linux/arm64)
- ✅ Pushes to private registry `registry.cloud-it.com.ar`
- ✅ Creates tags: `latest`, `sha-<commit>`, `<branch-name>`
- ✅ Uses Docker layer caching for faster builds

### 2. Update Manifests (`update-manifests`)
- ✅ Updates Kubernetes deployment manifest with new image tag
- ✅ Commits changes back to repository
- ✅ Only runs on `main` branch

### 3. Notify ArgoCD (`notify-argocd`)
- ✅ Confirms pipeline completion
- ✅ ArgoCD automatically detects changes and syncs

## 📋 ArgoCD Application

Deploy the ArgoCD application to start GitOps:

```bash
# Apply the ArgoCD application
kubectl apply -f argocd/application.yaml

# Check application status
kubectl get applications -n argocd

# View application details
kubectl describe application cognito-k3s-webhook -n argocd
```

## 🎯 Deployment Flow

1. **Developer pushes to main branch**
2. **GitHub Actions pipeline triggers**:
   - Builds Docker image
   - Pushes to registry
   - Updates K8s manifests
   - Commits changes
3. **ArgoCD detects changes**:
   - Syncs repository state
   - Deploys to `rrhh-agent` namespace
   - Self-heals if manual changes occur

## 🔍 Monitoring Deployment

### GitHub Actions
- Monitor pipeline: https://github.com/MatiasMartinez90/cognito-k3s-webhook/actions

### ArgoCD Dashboard
- Access ArgoCD UI to monitor sync status
- Application name: `cognito-k3s-webhook`
- Target namespace: `rrhh-agent`

### Kubernetes
```bash
# Check deployment status
kubectl get pods -n rrhh-agent
kubectl get deployment cognito-webhook -n rrhh-agent

# View logs
kubectl logs -f deployment/cognito-webhook -n rrhh-agent

# Check ingress
kubectl get ingress -n rrhh-agent
```

## 🐛 Troubleshooting

### Pipeline Fails at Registry Login
- Verify `REGISTRY_PASSWORD` secret is set correctly
- Check registry availability: `curl -I https://registry.cloud-it.com.ar`

### ArgoCD Not Syncing
- Check application health: `kubectl describe application cognito-k3s-webhook -n argocd`
- Manual sync: Use ArgoCD UI or CLI
- Verify repository access and permissions

### Deployment Issues
- Check pod status: `kubectl describe pod <pod-name> -n rrhh-agent`
- Verify image pull: Check for `ImagePullBackOff` errors
- Review resource limits and requests

## 🔒 Security Considerations

- ✅ Registry credentials stored as GitHub secrets
- ✅ Non-root container user (UID 1000)
- ✅ Resource limits enforced
- ✅ TLS termination at ingress
- ✅ ArgoCD RBAC controls deployment access

## 🚀 Manual Deployment (Alternative)

If needed, you can deploy manually without ArgoCD:

```bash
# Build and push image
./docker-build.sh

# Deploy to cluster
kubectl apply -f k8s/

# Verify deployment
kubectl get pods -n rrhh-agent
curl https://webhook-rrhh.cloud-it.com.ar/health
```

## 📊 Monitoring URLs

After successful deployment:

- **Health Check**: https://webhook-rrhh.cloud-it.com.ar/health
- **Test Endpoint**: https://webhook-rrhh.cloud-it.com.ar/test-webhook
- **Cognito Webhook**: https://webhook-rrhh.cloud-it.com.ar/cognito-webhook

## 🎯 Next Steps

1. **Configure GitHub secrets** (see above)
2. **Deploy ArgoCD application**: `kubectl apply -f argocd/application.yaml`
3. **Push changes to trigger pipeline**
4. **Monitor deployment** in ArgoCD dashboard
5. **Test webhook endpoints**
6. **Configure Cognito** to use webhook URL