"""
Simple FastAPI example service demonstrating IDP deployment.
This service includes health checks, metrics, and structured logging.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from datetime import datetime
import logging
import sys

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'API request duration')

app = FastAPI(
    title="Example API Service",
    description="Deployed via Internal Developer Platform",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Service starting up")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Service shutting down")

@app.get("/")
async def root():
    """Root endpoint"""
    REQUEST_COUNT.labels(method='GET', endpoint='/', status=200).inc()
    return {"message": "Welcome to the IDP-deployed API", "timestamp": datetime.now().isoformat()}

@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes probes"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "example-api"
    }

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint"""
    # Add dependency checks here (database, cache, etc.)
    return {"status": "ready", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest()

@app.get("/items/{item_id}")
async def get_item(item_id: int):
    """Example endpoint with path parameter"""
    REQUEST_COUNT.labels(method='GET', endpoint='/items', status=200).inc()
    
    if item_id < 0:
        REQUEST_COUNT.labels(method='GET', endpoint='/items', status=400).inc()
        raise HTTPException(status_code=400, detail="Item ID must be positive")
    
    logger.info(f"Fetching item {item_id}")
    
    return {
        "item_id": item_id,
        "name": f"Item {item_id}",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/items")
async def create_item(name: str, description: str = None):
    """Example POST endpoint"""
    REQUEST_COUNT.labels(method='POST', endpoint='/items', status=201).inc()
    logger.info(f"Creating item: {name}")
    
    return {
        "id": 123,
        "name": name,
        "description": description,
        "created_at": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
