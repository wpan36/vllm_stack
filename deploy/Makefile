SHELL := /bin/bash
COMPOSE := docker compose -f docker-compose.yml
FRONTEND := http://localhost:8081
BACKEND  := http://localhost:8080
PROM     := http://localhost:9090
GRAFANA  := http://localhost:3000

.PHONY: help build up down ps logs logs-be logs-fe smoke loadgen clean gpu-check open

help:
	@echo "LLM service targets:"
	@echo "  make build       - build backend & frontend images via compose"
	@echo "  make up          - start backend, frontend, prometheus, grafana"
	@echo "  make down        - stop and remove containers, network (keep volumes)"
	@echo "  make ps          - show running services"
	@echo "  make logs        - tail all logs"
	@echo "  make logs-be     - tail backend logs"
	@echo "  make logs-fe     - tail frontend logs"
	@echo "  make smoke       - quick health checks"
	@echo "  make loadgen     - send sample traffic to /generate"
	@echo "  make clean       - remove containers, network, and volumes"
	@echo "  make gpu-check   - check GPU availability (nvidia-smi)"
	@echo "  make open        - print service URLs"

build:
	$(COMPOSE) build backend frontend

up:
	$(COMPOSE) up -d
	@$(MAKE) open

down:
	$(COMPOSE) down

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f

logs-be:
	$(COMPOSE) logs -f backend

logs-fe:
	$(COMPOSE) logs -f frontend

open:
	@echo "Frontend  : $(FRONTEND)"
	@echo "Backend   : $(BACKEND)"
	@echo "Prometheus: $(PROM)"
	@echo "Grafana   : $(GRAFANA)"

smoke:
	@echo "[SMOKE] Checking frontend health..."
	@curl -fsS $(FRONTEND)/healthz && echo "" || (echo "Frontend health check failed" && exit 1)
	@echo "[SMOKE] Checking backend health..."
	@curl -fsS $(BACKEND)/healthz && echo "" || (echo "Backend health check failed" && exit 1)
	@echo "[SMOKE] Checking Prometheus targets..."
	@curl -fsS $(PROM)/-/ready && echo "" || (echo "Prometheus not ready" && exit 1)
	@echo "[SMOKE] OK"

# Simple load generator using curl; adjust COUNT/PAUSE as needed
COUNT ?= 30
PAUSE ?= 0.2
loadgen:
	@echo "[LOADGEN] Sending $(COUNT) requests to $(FRONTEND)/generate ..."
	@for i in $$(seq 1 $(COUNT)); do \
	  curl -sS -X POST "$(FRONTEND)/generate" \
	    -H "Content-Type: application/json" \
	    -d '{"prompts": ["1 + 1 equals:", "The capital of Japan is"]}' >/dev/null || true; \
	  sleep $(PAUSE); \
	done
	@echo "[LOADGEN] Done. Open Grafana at $(GRAFANA)"

clean:
	$(COMPOSE) down -v

gpu-check:
	@which nvidia-smi >/dev/null 2>&1 && nvidia-smi || \
	  (echo "nvidia-smi not found. Install NVIDIA drivers & nvidia-container-toolkit." && exit 1)
