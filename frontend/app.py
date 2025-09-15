import os
from prometheus_client import Counter, Histogram
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
import httpx
import asyncio
from pydantic import BaseModel
import json
import sys
import logging
import time


# basic settings
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8080")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "60"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))

# Prometheus metrics
REQUEST_COUNT = Counter("request_count_total", "Total requests to /generate via gateway")
ERROR_COUNT = Counter("error_count_total", "Total gateway errors on /generate")
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency in seconds", buckets=[0.1, 0.5, 1, 2, 5, 10, 20, 30, 60])

# logging settings
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(log, ensure_ascii=False)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("gateway")


app = FastAPI(title = "frontend")
Instrumentator().instrument(app).expose(app) #expose /metrics endpoint

httpClient: httpx.AsyncClient | None = None # Global HTTP client to send requests to backend
concurrency_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

class PromptRequest(BaseModel):
    prompts: list[str]

@app.on_event("startup")
async def startup_event():
    global httpClient
    print("Starting up and initializing HTTP client...")
    httpClient = httpx.AsyncClient(timeout=REQUEST_TIMEOUT, limits=httpx.Limits(max_keepalive_connections=20, max_connections=100))
    print("HTTP client initialized successfully.")
    logger.info(f"gateway_startup: backend_url={BACKEND_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    global httpClient
    if httpClient:
        await httpClient.aclose()
        httpClient = None
    print("HTTP client closed successfully.")
    logger.info("gateway_shutdown: HTTP client closed")

@app.get("/")
async def read_root():
    return {"message": "Welcome to the FastAPI Gateway!"}

@app.get("/healthz")
async def health_check():
    backendStatus = "unknown"
    up = 0
    try:
        assert httpClient is not None
        r = await httpClient.get(f"{BACKEND_URL}/healthz", timeout=3.0)
        if r.status_code == 200:
            data = r.json()
            backendStatus = data.get("status", "unknown")
            up = 1 if backendStatus == "ok" else 0
    except Exception as e:
        logger.error(f"backend_health_check_failed: {e}")

    return {"status": "ok", "backendStatus": backendStatus, "backendUp": up}

@app.post("/generate")
async def generate(payload: PromptRequest):
    global httpClient
    assert httpClient is not None
    REQUEST_COUNT.inc()
    start = time.time()

    async with concurrency_semaphore:
        try:
            resp = await httpClient.post(
                f"{BACKEND_URL}/generate",
                json=payload.model_dump(),
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code >= 500:
                ERROR_COUNT.inc()
                raise HTTPException(status_code=502, detail="backend error")

            if resp.status_code >= 400:
                ERROR_COUNT.inc()
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

            return resp.json()

        except HTTPException:
            raise
        except Exception as e:
            ERROR_COUNT.inc()
            logger.error(f"gateway_forward_failed: {e}")
            raise HTTPException(status_code=500, detail="gateway forward failed")
        finally:
            REQUEST_LATENCY.observe(time.time() - start)