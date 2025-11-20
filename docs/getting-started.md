# Getting Started with the Internal Developer Platform

This guide will walk you through deploying your first service using the IDP.

## Prerequisites

Before you begin, ensure you have:

- [ ] Access to the company Kubernetes cluster
- [ ] GitHub account with repository creation permissions
- [ ] Backstage access (https://backstage.company.com)
- [ ] kubectl configured and authenticated
- [ ] Docker installed locally (for testing)

## Your First Deployment in 15 Minutes

### Step 1: Create a New Service (5 minutes)

1. Navigate to Backstage: https://backstage.company.com
2. Click **"Create"** in the sidebar
3. Select **"Python API Service"** template
4. Fill in the form:
   - **Service Name**: my-first-api
   - **Description**: My first IDP-deployed service
   - **Team Owner**: Select your team
   - **Database Required**: No (for now)
   - **Redis Cache**: No
   - **Initial Replicas**: 2

5. Click **"Review"** then **"Create"**

The platform will now:
- ✅ Create a GitHub repository
- ✅ Generate service code from template
- ✅ Configure CI/CD pipeline
- ✅ Set up ArgoCD application
- ✅ Configure monitoring dashboards
- ✅ Register in service catalog

### Step 2: View Your New Service (2 minutes)

1. Click the **"Open in Backstage"** link
2. Explore the service overview:
   - **Overview Tab**: Service metadata and ownership
   - **CI/CD Tab**: Pipeline status and history
   - **Kubernetes Tab**: Pod status and logs
   - **Monitoring Tab**: Grafana dashboards
   - **Documentation Tab**: Auto-generated API docs

### Step 3: Make Your First Code Change (8 minutes)

1. Clone your new repository:
```bash
git clone https://github.com/company/my-first-api
cd my-first-api
```

2. Make a simple change to `main.py`:
```python
@app.get("/hello")
async def hello():
    return {"message": "Hello from my IDP service!"}
```

3. Test locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn main:app --reload

# Test the endpoint
curl http://localhost:8000/hello
```

4. Commit and push:
```bash
git add main.py
git commit -m "Add hello endpoint"
git push origin main
```

### Step 4: Watch the Automatic Deployment

1. Go to your service in Backstage
2. Click the **"CI/CD"** tab
3. Watch the pipeline execute:
   - 🧪 Running tests (2-3 min)
   - 🔨 Building image (2-3 min)
   - 🔍 Security scan (1-2 min)
   - 🚀 Deploying to staging (2-3 min)
   - ✅ Health check verification (30 sec)

**Total time: ~8-10 minutes**

### Step 5: Verify Your Deployment

1. Get the service URL from Backstage or:
```bash
kubectl get ingress -n my-first-api
```

2. Test your new endpoint:
```bash
curl https://my-first-api.staging.company.com/hello
```

3. Check the auto-configured monitoring:
```bash
# View logs
kubectl logs -n my-first-api -l app=my-first-api --tail=50

# Check metrics
curl https://my-first-api.staging.company.com/metrics
```

## What Just Happened?

Without any infrastructure configuration, you:

✅ Created a production-ready service
✅ Got automatic CI/CD pipeline
✅ Deployed to Kubernetes with autoscaling
✅ Got monitoring, logging, and metrics
✅ Configured health checks and readiness probes
✅ Set up service mesh integration
✅ Configured secrets management
✅ Got automatic SSL certificates

**All in 15 minutes.**

## Common Workflows

### Adding a Database

1. Go to your service in Backstage
2. Click **"Edit Service Configuration"**
3. Enable **"Database Required"**
4. Select database type (PostgreSQL/MySQL)
5. Save changes

The platform will:
- Provision database instance
- Create credentials and store in secrets
- Add connection configuration to your service
- Set up database migrations pipeline

### Deploying to Production

Production deployments require approval from your team lead:

1. Merge to `main` branch (deploys to staging automatically)
2. Test thoroughly in staging
3. Create a production deployment request:
```bash
# In your service repository
./scripts/promote-to-production.sh
```
4. Team lead approves in Backstage
5. Automatic deployment to production

### Scaling Your Service

```bash
# Scale up
kubectl scale deployment my-first-api -n my-first-api --replicas=5

# Or edit the values in deploy/staging/values.yaml:
replicas: 5
```

The platform also provides **automatic scaling** based on CPU/memory usage.

### Viewing Logs and Metrics

**Logs:**
```bash
# Real-time logs
kubectl logs -n my-first-api -l app=my-first-api -f

# Or use Kibana: https://kibana.company.com
```

**Metrics:**
- Grafana dashboards: https://grafana.company.com/d/my-first-api
- Prometheus queries: https://prometheus.company.com

**Distributed Tracing:**
- Jaeger UI: https://jaeger.company.com

## Getting Help

- 💬 Slack: #platform-engineering
- 📧 Email: platform-team@company.com
- 📚 Documentation: https://docs.company.com/platform
- 🐛 Report issues: https://github.com/company/platform-engineering-idp/issues

## FAQs

**Q: Can I use a different language/framework?**
A: Yes! We have templates for Go, Node.js, and Java. Check the template catalog in Backstage.

**Q: How do I rollback a deployment?**
A: The platform keeps the last 5 deployments. Use: `kubectl rollout undo deployment/my-first-api -n my-first-api`

**Q: Can I customize the CI/CD pipeline?**
A: Yes! Edit `.github/workflows/deploy.yml` in your repository.

**Q: What if I need infrastructure that's not in the template?**
A: Contact the platform team on Slack. We'll either help you configure it or add it to the template.

**Q: Is there a cost for using the platform?**
A: The platform itself is free. You're billed for actual infrastructure resources (compute, storage, etc.).

---

Ready to deploy more services? Head back to [Backstage](https://backstage.company.com) and create another one!
