from vllm import LLM, SamplingParams
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, time, sys, json, logging, threading
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# ---------------- basic settings ----------------
MODEL_PATH         = os.getenv("MODEL_PATH", "./models/Qwen2.5-1.5B-Instruct")
MODEL_DOWNLOAD_DIR = os.getenv("MODEL_DOWNLOAD_DIR", MODEL_PATH)
GPU_UTIL           = float(os.getenv("GPU_UTIL", "0.90"))
MAX_MODEL_LEN      = int(os.getenv("MAX_MODEL_LEN", "512"))
MAX_NUM_SEQS       = int(os.getenv("MAX_NUM_SEQS", "8"))
SWAP_SPACE         = float(os.getenv("SWAP_SPACE", "0.5"))
WARMUP             = os.getenv("WARMUP", "1") == "1"

# ---------------- logging ----------------
class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }, ensure_ascii=False)

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger("backend")

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# ---------------- app & metrics ----------------
app = FastAPI(title="backend")
Instrumentator().instrument(app).expose(app)  # /metrics

REQ_TOTAL   = Counter("llm_generate_requests_total", "Total LLM generate requests")
REQ_ERRORS  = Counter("llm_generate_errors_total",  "Total LLM generate errors")
REQ_LATENCY = Histogram(
    "llm_generate_latency_seconds",
    "Latency of LLM generation in seconds",
    buckets=[0.1, 0.5, 1, 2, 5, 10, 20, 30, 60]
)

llm = None
ready = False
sampling_params = SamplingParams(temperature=0.2, top_p=0.95, max_tokens=100)

class PromptRequest(BaseModel):
    prompts: list[str]

def _load_model_background():
    global llm, ready
    try:
        logger.info(
            f"initializing llm model={MODEL_PATH} download_dir={MODEL_DOWNLOAD_DIR} "
            f"gpu_util={GPU_UTIL} max_model_len={MAX_MODEL_LEN} max_num_seqs={MAX_NUM_SEQS} swap_space={SWAP_SPACE}"
        )
        llm = LLM(
            model=MODEL_PATH,
            download_dir=MODEL_DOWNLOAD_DIR,
            swap_space=SWAP_SPACE,
            gpu_memory_utilization=GPU_UTIL,
            max_model_len=MAX_MODEL_LEN,
            max_num_seqs=MAX_NUM_SEQS,
        )
        logger.info("llm_loaded")
        if WARMUP:
            logger.info("warmup_begin")
            _ = llm.generate(["hello"], SamplingParams(max_tokens=1, temperature=0.0))
            logger.info("warmup_done")
        ready = True
        logger.info("backend_ready")
    except Exception as e:
        logger.error(f"llm_init_failed: {e}")

@app.on_event("startup")
async def startup_event():
    threading.Thread(target=_load_model_background, daemon=True).start()

@app.get("/")
def root():
    return {"service": "backend", "model": MODEL_PATH, "ready": ready}

@app.get("/healthz")
def healthz():
    return {"status": "ok", "ready": ready}

@app.post("/generate")
def generate_response(request: PromptRequest):
    global llm
    if llm is None:
        raise HTTPException(status_code=503, detail="LLM not initialized yet")
    start = time.time()
    REQ_TOTAL.inc()
    try:
        outputs = llm.generate(request.prompts, sampling_params)
        return {"outputs": [
            {"prompt": out.prompt, "output": out.outputs[0].text} for out in outputs
        ]}
    except Exception as e:
        REQ_ERRORS.inc()
        logger.error(f"inference_failed: {e}")
        raise HTTPException(status_code=500, detail="inference failed")
    finally:
        REQ_LATENCY.observe(time.time() - start)
