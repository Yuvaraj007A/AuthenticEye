# AuthenticEye Platform — Deployment & Monitoring Guide

This guide provides instructions to deploy the AuthenticEye platform locally or to production, configure environment variables, and verify performance monitoring.

---

## 1. Environment Configurations

Create a `.env` file in the root directory. Below are the key environment configurations:

```env
# Backend gateway configuration
PORT=5000
MONGO_URI=mongodb://localhost:27017/authenticeye
JWT_SECRET=your_super_secret_jwt_key
FRONTEND_URL=http://localhost:5173

# AI FastAPI Microservice Link
AI_SERVICE_URL=http://localhost:8000

# Error Tracking (Optional)
SENTRY_DSN=your_sentry_dsn_token
```

---

## 2. Docker Compose Deployment

The quickest way to spin up the entire system (Frontend, Backend, AI Microservice, MongoDB, Prometheus, Grafana) is via Docker Compose.

```bash
# Clone the repository and build images
docker compose build

# Start services in the background
docker compose up -d

# Verify all containers are running
docker compose ps
```

### Exposed Ports
- **Frontend App**: [http://localhost:80](http://localhost:80)
- **Backend API Gateway**: [http://localhost:5000](http://localhost:5000)
- **AI Microservice**: [http://localhost:8000](http://localhost:8000)
- **Prometheus Dashboard**: [http://localhost:9090](http://localhost:9090)
- **Grafana Visualization Panel**: [http://localhost:3000](http://localhost:3000)

---

## 3. Performance Monitoring & Alerting

### A. Prometheus Setup
Prometheus is configured via `./monitoring/prometheus/prometheus.yml` to scrap metrics from both the Express.js gateway and FastAPI microservice at regular 15-second intervals.
- Express metrics endpoint: `http://backend:5000/metrics`
- FastAPI metrics endpoint: `http://ai-service:8000/metrics`

### B. Grafana Setup
1. Open Grafana at [http://localhost:3000](http://localhost:3000).
2. Log in using default credentials:
   - **Username**: `admin`
   - **Password**: `admin` (you will be prompted to change it on first login)
3. The Prometheus datasource is automatically provisioned.
4. The **AuthenticEye Platform Metrics** dashboard comes preconfigured and displays:
   - Request volumes by HTTP path and status code.
   - 95th-percentile (p95) model inference latency trends.
   - Total deepfake detection counts categorized by media format (images vs videos).

### C. Sentry SDK Setup
Sentry SDKs are integrated into both backend servers. If `SENTRY_DSN` is set in the environment, Sentry will capture runtime exceptions, log performance traces, and forward warnings to your project dashboard.
