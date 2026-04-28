# 06 · Local vLLM + Gemma 4B Sovereign Edge Deployment (P2)

**Goal**: Replace Gemini 3 Flash cloud calls with **fully local** vLLM + Google Gemma 4B inference. Required for true Data Sovereignty (Sovereign Edge tier — see whitepaper §2A). Customer's data never leaves their VPC.

## Why this is the headline feature
The "Sovereign Edge" promise is the entire commercial differentiator vs. ChatGPT/Anthropic-based competitors. Without this, the marketing claim "raw data never leaves your tenant" is false.

## Cannot be done in current pod
- Kubernetes pod has no GPU
- vLLM requires CUDA 12.x + min 8GB VRAM for Gemma 4B (16GB recommended)
- Implement and test in customer's GPU-equipped infrastructure (or AWS p3, GCP A100, etc.)

## Estimated effort
2-3h once GPU node exists.

## Architecture
```
[Tenant pod]
  ├─ FastAPI backend (port 8001)
  └─ vLLM server (port 8002)  ← Gemma 4B, OpenAI-compatible API
```

## Steps

### 1. Add vLLM service to `docker-compose.yml`
```yaml
  vllm:
    image: vllm/vllm-openai:latest
    runtime: nvidia
    environment:
      HUGGING_FACE_HUB_TOKEN: ${HF_TOKEN}
    command: >
      --model google/gemma-4b-it
      --dtype bfloat16
      --max-model-len 8192
      --gpu-memory-utilization 0.85
    ports: ["8002:8000"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              capabilities: [gpu]
```

### 2. Update `backend/.env`
```
VLLM_BASE_URL=http://vllm:8000/v1
VLLM_MODEL=google/gemma-4b-it
USE_LOCAL_LLM=true
```

### 3. Update `services/ai.py` (after split — see doc 02)
```python
import os
from openai import AsyncOpenAI

if os.environ.get("USE_LOCAL_LLM") == "true":
    _llm = AsyncOpenAI(base_url=os.environ["VLLM_BASE_URL"], api_key="not-needed")
    _model = os.environ["VLLM_MODEL"]
else:
    # current emergentintegrations Gemini path
    _llm = None

async def analyze_signal_ai(content: str, ctx: str = "") -> dict:
    if _llm:
        # Local vLLM — strict JSON mode via guided_json
        resp = await _llm.chat.completions.create(
            model=_model,
            messages=[
                {"role": "system", "content": AI_SYSTEM_PROMPT},
                {"role": "user", "content": f"STRATEGY:\n{ctx}\n\nSIGNAL:\n{content}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            extra_body={"guided_json": SIGNAL_SCHEMA_JSON},  # vLLM extension
        )
        return json.loads(resp.choices[0].message.content)
    # else: existing Gemini path
```

### 4. Pydantic strict mode
Use `strict=True` and JSON Schema for guided generation:
```python
SIGNAL_SCHEMA_JSON = {
    "type": "object",
    "properties": {
        "risk_level": {"enum": ["LOW", "MODERATE", "HIGH", "CRITICAL"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "summary": {"type": "string", "maxLength": 500},
        "execution_gaps": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "hidden_assumptions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "facilitator_questions": {"type": "array", "items": {"type": "string"}, "maxItems": 5},
        "category": {"enum": ["resources", "capabilities", "engagement", "process"]},
    },
    "required": ["risk_level", "confidence", "summary", "execution_gaps", "category"],
}
```

### 5. Fine-tuning (optional, P3)
Gemma 4B base will work but fine-tune on Finnish strategic analysis corpus for production quality. Use LoRA + Unsloth for cost-effective fine-tune.

### 6. Performance targets
- p50 latency < 800ms per signal analysis (single A100, ~150 tokens out)
- Continuous batching: target 32 concurrent requests
- Use `--enable-prefix-caching` to share strategy RAG context across signals

## Success criteria
- [ ] All AI calls now go to internal vLLM endpoint (verify via tcpdump — zero outbound LLM API traffic)
- [ ] JSON parse rate = 100% (guided_json eliminates hallucinated keys)
- [ ] Pytest suite passes with `USE_LOCAL_LLM=true`
- [ ] CISO sign-off: data never leaves customer VPC

## Failsafe
Keep `USE_LOCAL_LLM=false` flag — falls back to Gemini if vLLM unhealthy (with explicit logged warning that Sovereign Edge is breached).
