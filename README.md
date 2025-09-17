# vllm_stack: LLM Inference Microservices (vLLM + FastAPI)

A production-style LLM inference stack that packages a model into **standardized microservices** with **observability** and **automation**:

- **Backend**: vLLM + FastAPI exposing `/generate`, `/healthz`, `/metrics`
- **Gateway**: FastAPI API gateway with concurrency limits, unified timeouts, error attribution
- **Observability**: Prometheus + Grafana (QPS / p95 latency / error rate + targets health)
- **Automation**: Docker/Compose one-command run, Makefile helpers, GitHub Actions → GHCR
- **Kubernetes**: GPU-aware scheduling (`nvidia.com/gpu:1`), probes, ServiceMonitor auto-scrape
- **Portable**: Runs on **laptop**, **minikube**, and **cloud** using the same images & env

> ⚠️ **Note**: This project can be used as a **reference LLM microservice**. If you plan to use it directly, **review & harden config** (e.g., change the **Grafana admin password** in docker-compose, set resource limits, enable auth/rate-limit on the gateway, etc.).

---

## Table of Contents

- [What You Can Do With This](#what-you-can-do-with-this)
- [Architecture](#architecture)
- [Quick Start (Docker Compose)](#quick-start-docker-compose)
- [Observability: Prometheus & Grafana](#observability-prometheus--grafana)
- [Configuration (ENV)](#configuration-env)
- [Troubleshooting](#troubleshooting)

---

## What You Can Do With This

- Spin up a **standardized LLM inference API** quickly for experiments, demos, or POCs
- Measure **throughput (QPS)**, **latency (p95)**, and **error rate** end-to-end
- Validate **GPU scheduling** and **scaling** patterns (frontend scale-out, backend pinned to GPU)
- Use as a **template** to build your own microservice (swap models, tune params, add auth)

---

## Architecture


```text
Client → Gateway (FastAPI)
             ↘ /metrics
          Backend (vLLM + FastAPI)
                ↘ /metrics
Prometheus ← scrapes both /metrics
Grafana    ← visualizes QPS / p95 / error rate / targets up
```
- **Gateway**: user-facing entry; applies concurrency limits, timeouts, error propagation; exposes gateway metrics.
- **Backend**: vLLM inference service; exposes business metrics via Prometheus (requests_total, latency_seconds_bucket, errors_total).
- **Prometheus/Grafana**: scrape + dashboards; p95 is computed via histogram_quantile() from histograms.

## Quick Start (Docker Compose)
From `/deploy/`:
```text
# build images
make build

# start the stack (backend, frontend, prometheus, grafana)
make up

# quick health checks
make smoke

# send sample traffic (drives metrics)
make loadgen
```

## Observability: Prometheus & Grafana
Metrics include:
  - Requests: `/llm_generate_requests_total`, `/gateway_generate_requests_total`
  - Errors: `/llm_generate_errors_total`, `/gateway_generate_errors_total`
  - Latency histograms: `/llm_generate_latency_seconds_bucket`, `/gateway_generate_latency_seconds_bucket`

## Configuration (ENV)
Key backend env:
- `/MODEL_PATH` / `/MODEL_DOWNLOAD_DIR` — model weights path (mounted volume in Compose/K8s)
- `/GPU_UTIL` — target GPU memory utilization (e.g., 0.90)
- `/MAX_MODEL_LEN`, `/MAX_NUM_SEQS`, `/SWAP_SPACE`, `/WARMUP`

## Troubleshooting
**1. Backend exits after some time with no explicit error**
Check the container exit code:
```text
docker ps -a | grep backend
docker inspect <backend-container-id> --format='{{.State.ExitCode}}'
```
If you see `/137`, it usually means the process was killed by **OOM** (out-of-memory). This can happen when resources are tight.
- Try reducing `/SWAP_SPACE` or other parameters (e.g., `/MAX_NUM_SEQS`, `/MAX_MODEL_LEN`, sampling length).
- Lower `/GPU_UTIL`, or increase `/shm_size` (Compose already sets `/shm_size`: "2g").
- Ensure your model fits the available GPU memory.

 
**2. Grafana login**
  
  Default admin password is admin (set in docker-compose).
