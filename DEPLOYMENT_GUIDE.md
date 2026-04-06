# Production Deployment Guide

This guide covers deploying the Medical Lab Report Extraction API to production.

## 🚀 Local Production Test

Before deploying to cloud, test locally with production settings:

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --timeout 120
```

---

## 🐳 Docker Deployment

### Build and Run Locally

```bash
# Build image
docker build -t lab-report-api:latest .

# Run container
docker run -p 8000:8000 \
  -e API_HOST=0.0.0.0 \
  -e API_PORT=8000 \
  lab-report-api:latest
```

### Push to Docker Registry

```bash
# Login to your registry (Docker Hub, ECR, GCR, etc.)
docker login

# Tag image
docker tag lab-report-api:latest myregistry/lab-report-api:latest

# Push
docker push myregistry/lab-report-api:latest
```

---

## Docker Compose (Multi-container)

For production with Nginx reverse proxy:

```bash
docker-compose up -d
```

This runs:
- API service (4 instances behind load balancer in production)
- Nginx reverse proxy with SSL/TLS
- Persistent volumes for logs and reports

---

## ☁️ Cloud Platform Deployments

### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/lab-report-api

# Deploy
gcloud run deploy lab-report-api \
  --image gcr.io/PROJECT_ID/lab-report-api \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --timeout 300
```

### AWS Elastic Container Service (ECS)

1. Create ECR repository:
```bash
aws ecr create-repository --repository-name lab-report-api
```

2. Push image:
```bash
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/lab-report-api:latest
```

3. Create ECS task definition (lab-report-api-task.json):
```json
{
  "family": "lab-report-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "lab-report-api",
      "image": "ACCOUNT.dkr.ecr.REGION.amazonaws.com/lab-report-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/lab-report-api",
          "awslogs-region": "REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

4. Register task and create service:
```bash
aws ecs register-task-definition --cli-input-json file://lab-report-api-task.json
aws ecs create-service --cluster my-cluster --service-name lab-report-api \
  --task-definition lab-report-api --desired-count 2 --launch-type FARGATE
```

### Heroku

1. Create `Procfile`:
```
web: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

2. Create `runtime.txt`:
```
python-3.10.12
```

3. Deploy:
```bash
heroku login
heroku create lab-report-api
git push heroku main
heroku logs --tail
```

### Azure App Service

1. Create App Service plan and app:
```bash
az appservice plan create -g myResourceGroup -n myAppServicePlan --sku B2
az webapp create -g myResourceGroup -p myAppServicePlan -n lab-report-api
```

2. Deploy from local git or GitHub

3. Configure app settings:
```bash
az webapp config appsettings set -g myResourceGroup -n lab-report-api \
  --settings API_PORT=80 LOG_LEVEL=INFO
```

---

## 📊 Performance Optimization

### Gunicorn Configuration

For CPU-intensive OCR workloads:

```bash
# Using sync workers with high timeout
gunicorn -w 2 \
  -k uvicorn.workers.UvicornWorker \
  --worker-class=uvicorn.workers.UvicornWorker \
  --workers=2 \
  --timeout=180 \
  --max-requests=1000 \
  --max-requests-jitter=100 \
  main:app
```

### Caching with Redis

For high-traffic scenarios, add Redis caching:

```python
# In main.py
from redis import Redis
from functools import lru_cache

redis_client = Redis(host='localhost', port=6379, db=0)

@app.post("/scan-report")
async def scan_report(file: UploadFile = File(...)):
    # Check cache first
    file_hash = hashlib.md5(await file.read()).hexdigest()
    cached = redis_client.get(f"report:{file_hash}")
    
    if cached:
        return json.loads(cached)
    
    # ... process and cache result ...
```

### Database Connection Pooling

For persistent storage:

```bash
pip install sqlalchemy psycopg2-binary
```

---

## 🔒 Security Best Practices

### 1. API Authentication

Add API key authentication:

```python
# In main.py
from fastapi import Header, HTTPException

@app.post("/scan-report")
async def scan_report(
    file: UploadFile = File(...),
    x_api_key: str = Header(None)
):
    if not x_api_key or x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    # ... rest of endpoint
```

### 2. Rate Limiting

```bash
pip install slowapi
```

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/scan-report")
@limiter.limit("10/minute")
async def scan_report(request: Request, file: UploadFile = File(...)):
    # ...
```

### 3. HTTPS/SSL

Configure Nginx with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

### 4. Environment Variables

Never hardcode secrets:

```bash
export API_KEY="your-secure-key"
export DATABASE_URL="postgresql://user:pass@host/db"
export SENTRY_DSN="https://..."
```

---

## 📈 Monitoring & Logging

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

request_count = Counter('api_requests_total', 'Total requests')
request_duration = Histogram('api_request_duration_seconds', 'Request duration')

@app.post("/scan-report")
async def scan_report(file: UploadFile = File(...)):
    request_count.inc()
    with request_duration.time():
        # ... process request
```

### Error Tracking (Sentry)

```python
import sentry_sdk

sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    traces_sample_rate=0.1,
    environment="production"
)
```

### Centralized Logging

```bash
pip install python-json-logger
```

```python
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Example

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v2
        with:
          push: true
          tags: gcr.io/${{ secrets.GCP_PROJECT }}/lab-report-api:latest
          
      - name: Deploy to Cloud Run
        uses: google-github-actions/deploy-cloudrun@v0
        with:
          service: lab-report-api
          image: gcr.io/${{ secrets.GCP_PROJECT }}/lab-report-api:latest
          region: us-central1
```

---

## 🧪 Production Testing Checklist

- [ ] Load test with Apache Bench or Locust
- [ ] Stress test with realistic file sizes
- [ ] Test with slow network connections
- [ ] Test error handling and recovery
- [ ] Verify logging output
- [ ] Test auto-scaling policies
- [ ] Check database connection pooling
- [ ] Verify CORS configuration
- [ ] Test rate limiting
- [ ] Verify API authentication
- [ ] Test database backups
- [ ] Verify SSL/TLS certificates
- [ ] Monitor memory usage
- [ ] Monitor CPU usage
- [ ] Check disk space requirements

---

## 📊 Scaling Strategies

### Horizontal Scaling

Run multiple instances behind a load balancer:

```bash
# AWS ELB / ALB
aws elbv2 create-load-balancer --name lab-report-api-lb

# Google Cloud Load Balancer
gcloud compute load-balancers create lab-report-api-lb
```

### Vertical Scaling

Increase resources for single instance:

```bash
# Increase memory
docker run -m 4g lab-report-api:latest

# Increase CPU workers
gunicorn -w 8 main:app
```

### Auto-scaling

Configure auto-scaling policies:

```bash
# AWS Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name lab-report-api-asg \
  --desired-capacity 3 \
  --max-size 10 \
  --min-size 1
```

---

## 📞 Support & Troubleshooting

### Check Container Logs

```bash
# Docker
docker logs <container-id>

# Kubernetes
kubectl logs <pod-name>

# Cloud Run
gcloud run logs read lab-report-api --region us-central1
```

### Performance Investigation

```bash
# Monitor resource usage
docker stats

# Check network
netstat -an | grep 8000

# Profile with cProfile
python -m cProfile -o stats.prof main.py
```

---

See main README.md for API documentation and local development guide.
