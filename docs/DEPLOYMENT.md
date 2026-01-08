# Deployment Guide - MomWatch AI

Production deployment guide for MomWatch AI maternal health monitoring system.

---

## Pre-Deployment Checklist

### 1. Security Configuration

- [ ] **Generate Strong JWT Secret**
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
  Add to `.env` as `JWT_SECRET`

- [ ] **Obtain Zudu AI API Key**
  - Sign up at https://zudu.ai
  - Get API key from dashboard
  - Add to `.env` as `ZUDU_API_KEY`

- [ ] **Configure MongoDB Authentication**
  ```yaml
  # docker-compose.yml
  mongodb:
    environment:
      MONGO_INITDB_ROOT_USERNAME: admin
      MONGO_INITDB_ROOT_PASSWORD: <strong-password>
  ```

- [ ] **Review CORS Settings**
  - Update `CORS_ORIGINS` in `.env` with production domains
  - Example: `["https://app.momwatch.ai"]`

### 2. Infrastructure Requirements

**Minimum Specifications:**
- **CPU:** 2 cores
- **RAM:** 4GB (8GB recommended)
- **Storage:** 20GB SSD
- **Network:** 100 Mbps

**Recommended Production:**
- **CPU:** 4+ cores
- **RAM:** 16GB
- **Storage:** 100GB SSD with RAID
- **Network:** 1 Gbps

### 3. Domain & SSL

- [ ] Register domain (e.g., momwatch.ai)
- [ ] Set up DNS records
  - `A` record: `app.momwatch.ai` → Server IP
  - `A` record: `api.momwatch.ai` → Server IP
- [ ] Obtain SSL certificates (Let's Encrypt recommended)

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Single Server)

#### 1. Install Docker

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

#### 2. Clone Repository

```bash
git clone https://github.com/yourusername/momwatch_ai.git
cd momwatch_ai
```

#### 3. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit all configuration values
```

#### 4. Train ML Model

```bash
# Generate dataset
docker-compose run --rm backend python ml_ops/dataset_gen.py

# Train model
docker-compose run --rm backend python ml_ops/train.py

# Evaluate
docker-compose run --rm backend python ml_ops/evaluate.py
```

#### 5. Start Services

```bash
docker-compose up -d
```

#### 6. Verify Deployment

```bash
# Check service health
docker-compose ps

# Check logs
docker-compose logs -f backend

# Test API
curl http://localhost:8000/system/health

# Access frontend
open http://localhost:8501
```

#### 7. Set Up Reverse Proxy (Nginx)

**Install Nginx:**
```bash
sudo apt install nginx certbot python3-certbot-nginx
```

**Configure:**
```nginx
# /etc/nginx/sites-available/momwatch
server {
    listen 80;
    server_name app.momwatch.ai;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}

server {
    listen 80;
    server_name api.momwatch.ai;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Enable and get SSL:**
```bash
sudo ln -s /etc/nginx/sites-available/momwatch /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d app.momwatch.ai -d api.momwatch.ai
```

---

### Option 2: Kubernetes (Multi-Server Production)

Coming soon...

---

## Database Backup Strategy

### Automated Daily Backups

**Create backup script:**
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR="/var/backups/momwatch"
DATE=$(date +%Y%m%d_%H%M%S)

docker exec momwatch_mongodb mongodump \
  --out=/backup/mongodb_$DATE \
  --gzip

# Keep last 30 days
find $BACKUP_DIR -type d -mtime +30 -exec rm -rf {} +
```

**Add to crontab:**
```bash
0 2 * * * /opt/momwatch/backup.sh
```

### Restore from Backup

```bash
docker exec -i momwatch_mongodb mongorestore \
  --gzip \
  /backup/mongodb_20260108_020000
```

---

## Monitoring Setup

### 1. Health Checks

**Systemd service for monitoring:**
```ini
# /etc/systemd/system/momwatch-monitor.service
[Unit]
Description=MomWatch Health Monitor
After=docker.service

[Service]
Type=simple
ExecStart=/opt/momwatch/health_monitor.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

**health_monitor.sh:**
```bash
#!/bin/bash
while true; do
  HEALTH=$(curl -s http://localhost:8000/system/health | jq -r .status)
  
  if [ "$HEALTH" != "healthy" ]; then
    echo "ALERT: System unhealthy at $(date)" | mail -s "MomWatch Alert" admin@momwatch.ai
  fi
  
  sleep 300  # Check every 5 minutes
done
```

### 2. Log Management

**Rotate logs:**
```
# /etc/logrotate.d/momwatch
/var/log/momwatch/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root adm
    sharedscripts
}
```

### 3. Metrics (Optional - Prometheus)

**docker-compose.yml addition:**
```yaml
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```

---

## Scaling Considerations

### Horizontal Scaling

**Backend API:**
- Increase `API_WORKERS` in `.env`
- Deploy multiple backend containers
- Use load balancer (Nginx/HAProxy)

**Database:**
- MongoDB replica set for high availability
- Sharding for large datasets

**ML Model:**
- Model caching in Redis
- Separate inference service

### Vertical Scaling

- Increase container resource limits in `docker-compose.yml`:
```yaml
backend:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 4G
```

---

## Security Hardening

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 2. Docker Security

- Run containers as non-root user
- Use Docker secrets for sensitive data
- Enable Docker Content Trust

### 3. Application Security

- Enable rate limiting
- Implement API key authentication for Zudu AI
- Regular security audits
- Keep dependencies updated

---

## Maintenance Procedures

### Regular Updates

**Monthly:**
```bash
# Backup database
./backup.sh

# Pull latest code
git pull origin main

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify health
docker-compose ps
curl http://localhost:8000/system/health
```

### Model Retraining

**Quarterly or when accuracy drops:**
```bash
# Generate new dataset with latest data
docker-compose exec backend python ml_ops/dataset_gen.py

# Retrain
docker-compose exec backend python ml_ops/train.py

# Evaluate
docker-compose exec backend python ml_ops/evaluate.py

# Compare metrics before deploying
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs backend

# Check disk space
df -h

# Check port conflicts
sudo netstat -tulpn | grep :8000
```

### Database Connection Issues

```bash
# Test MongoDB
docker exec momwatch_mongodb mongo --eval "db.adminCommand('ping')"

# Check network
docker network inspect momwatch_network
```

### ML Model Errors

```bash
# Verify model files
docker exec momwatch_backend ls -lh /app/models/

# Check circuit breaker status
curl http://localhost:8000/system/health | jq .circuit_breaker
```

---

## Rollback Procedure

If deployment fails:

```bash
# Stop current version
docker-compose down

# Checkout previous version
git checkout <previous-commit-hash>

# Rebuild and start
docker-compose build
docker-compose up -d

# Restore database if needed
docker exec -i momwatch_mongodb mongorestore --gzip /backup/mongodb_<timestamp>
```

---

## Performance Tuning

### MongoDB Optimization

```javascript
// Create indexes
db.users.createIndex({"email": 1}, {unique: true})
db.triage_logs.createIndex({"user_id": 1, "timestamp": -1})
db.idempotency_keys.createIndex({"created_at": 1}, {expireAfterSeconds: 600})
```

### API Response Time

- Enable caching for frequently accessed data
- Use connection pooling (already configured)
- Monitor slow queries

---

## Compliance & Legal

### HIPAA Compliance Checklist

- [ ] Encrypt data at rest (MongoDB encryption)
- [ ] Encrypt data in transit (HTTPS/TLS)
- [ ] Access logging and audit trails
- [ ] User authentication and authorization
- [ ] Regular security assessments
- [ ] Business Associate Agreements (BAA) with vendors

### Data Retention Policy

- Triage logs: Retain 7 years
- User data: Delete upon request (GDPR)
- Backups: 30 days rotating

---

## Support & Escalation

**Priority Levels:**

1. **P1 - Critical:** System down, data loss
   - Response: Immediate
   - Escalation: After 1 hour

2. **P2 - High:** Major feature broken
   - Response: 2 hours
   - Escalation: After 4 hours

3. **P3 - Medium:** Minor issue
   - Response: 1 business day

4. **P4 - Low:** Enhancement request
   - Response: 1 week

---

## Cost Estimation

### Cloud Hosting (AWS/Azure/GCP)

**Small Deployment (100 users):**
- Compute: $50/month
- Database: $30/month
- Storage: $10/month
- Total: ~$90/month

**Medium Deployment (1000 users):**
- Compute: $200/month
- Database: $100/month
- Storage: $30/month
- Total: ~$330/month

**Large Deployment (10,000+ users):**
- Compute: $1000/month
- Database: $500/month
- Storage: $100/month
- Total: ~$1600/month

*Prices are estimates and vary by provider.*

---

## Contact for Production Support

- **Technical Issues:** support@momwatch.ai
- **Security Issues:** security@momwatch.ai
- **Emergency Hotline:** 1-800-MOMWATCH

---

**Last Updated:** January 8, 2026  
**Version:** 1.0.0
