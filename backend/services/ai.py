"""
TALK TO+ BDaaS — AI helpers (Gemini 3 Flash via Emergent LLM key, optional vLLM).
"""
import json
import uuid
from typing import List

from core import logger, EMERGENT_LLM_KEY, USE_LOCAL_LLM, VLLM_BASE_URL, VLLM_MODEL
from models import RiskLevel, BottleneckCategory


AI_SYSTEM_PROMPT = """You are TALK TO+ BDaaS Local Node — an enterprise execution-risk analyst.
Your job is to stress-test signals against company strategy and expose hidden execution gaps.
You respond ONLY with strict JSON, no markdown, no prose. Schema:
{
 "risk_level": "LOW|MODERATE|HIGH|CRITICAL",
 "confidence": 0.0-1.0,
 "summary": "2 sentences, language matching input",
 "execution_gaps": ["gap1", "gap2"],
 "hidden_assumptions": ["assumption1"],
 "facilitator_questions": ["question1", "question2"],
 "category": "resources|capabilities|engagement|process"
}
Be direct, critical, Finnish-enterprise blunt when input is Finnish. Focus on execution, not strategy itself."""


PRESCRIPTIVE_PROMPT = """You are TALK TO+ BDaaS Prescriptive Engine.
Generate an Action Card playbook based on a validated execution risk and universal success patterns.
Respond ONLY with strict JSON:
{
 "title": "short title (max 80 chars)",
 "summary": "1-2 sentence description, language matching input",
 "playbook": ["step 1", "step 2", "step 3", "step 4", "step 5"]
}
Be specific, operational, enterprise-ready."""


async def _llm_chat_json(system_prompt: str, user_text: str, session_id: str) -> str:
    """Unified LLM call. If USE_LOCAL_LLM=true → vLLM (OpenAI-compatible).
    Else → Gemini 3 Flash via emergentintegrations. Returns raw response text."""
    if USE_LOCAL_LLM and VLLM_BASE_URL:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(base_url=VLLM_BASE_URL, api_key="not-needed")
            resp = await client.chat.completions.create(
                model=VLLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=800,
            )
            return resp.choices[0].message.content or ""
        except ImportError:
            logger.error("openai package missing; falling back to Gemini")
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system_prompt,
    ).with_model("gemini", "gemini-3-flash-preview")
    return await chat.send_message(UserMessage(text=user_text))


async def analyze_signal_ai(content: str, strategy_context: str = "") -> dict:
    try:
        user_text = f"STRATEGY CONTEXT:\n{strategy_context[:2000]}\n\nSIGNAL:\n{content}\n\nReturn JSON only."
        resp = await _llm_chat_json(AI_SYSTEM_PROMPT, user_text, f"signal-{uuid.uuid4()}")
        txt = resp.strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            if txt.startswith("json"):
                txt = txt[4:]
        parsed = json.loads(txt.strip())
        rl = parsed.get("risk_level", "MODERATE").upper()
        if rl not in [e.value for e in RiskLevel]:
            rl = "MODERATE"
        cat = parsed.get("category", "process").lower()
        if cat not in [e.value for e in BottleneckCategory]:
            cat = "process"
        return {
            "risk_level": rl,
            "confidence": float(parsed.get("confidence", 0.7)),
            "summary": parsed.get("summary", "")[:500],
            "execution_gaps": list(parsed.get("execution_gaps", []))[:5],
            "hidden_assumptions": list(parsed.get("hidden_assumptions", []))[:5],
            "facilitator_questions": list(parsed.get("facilitator_questions", []))[:5],
            "category": cat,
        }
    except Exception as e:
        logger.warning(f"AI analysis fallback: {e}")
        low_kw = ["onnistui", "hyvä", "stable", "good", "works"]
        crit_kw = ["kriittinen", "critical", "urgent", "failing", "blocker", "resurssipula"]
        high_kw = ["huoli", "concern", "risk", "issue", "problem", "ongelma"]
        c = content.lower()
        if any(k in c for k in crit_kw):
            rl = "CRITICAL"
        elif any(k in c for k in high_kw):
            rl = "HIGH"
        elif any(k in c for k in low_kw):
            rl = "LOW"
        else:
            rl = "MODERATE"
        return {
            "risk_level": rl,
            "confidence": 0.55,
            "summary": f"Heuristinen analyysi (AI-yhteys offline). Signaali viittaa tasoon {rl}.",
            "execution_gaps": ["Yksityiskohtainen toimeenpano vaatii tarkennusta"],
            "hidden_assumptions": ["Oletetaan nykyinen kapasiteetti riittää"],
            "facilitator_questions": ["Mitä konkreettista tukea tarvitaan?", "Kuka omistaa tämän ongelman?"],
            "category": "process",
        }


async def generate_action_card_ai(signal_summary: str, gaps: List[str], patterns: List[str]) -> dict:
    try:
        msg = f"""VALIDATED SIGNAL:\n{signal_summary}\n\nEXECUTION GAPS:\n{chr(10).join('- '+g for g in gaps)}\n\nUNIVERSAL SUCCESS PATTERNS FROM SWARM:\n{chr(10).join('- '+p for p in patterns) or '(none yet)'}\n\nReturn JSON."""
        resp = await _llm_chat_json(PRESCRIPTIVE_PROMPT, msg, f"card-{uuid.uuid4()}")
        txt = resp.strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            if txt.startswith("json"):
                txt = txt[4:]
        p = json.loads(txt.strip())
        return {
            "title": p.get("title", "Playbook")[:120],
            "summary": p.get("summary", "")[:500],
            "playbook": list(p.get("playbook", []))[:10],
        }
    except Exception as e:
        logger.warning(f"Action card fallback: {e}")
        return {
            "title": f"Interventio: {signal_summary[:60]}",
            "summary": "Suositeltu korjaava toimenpideketju perustuen havaittuihin toimeenpanoaukkoihin.",
            "playbook": [
                "1. Kutsu omistaja ja sidosryhmät 48h sisään",
                "2. Kartoita kapasiteetti ja resurssit vs. tavoite",
                "3. Määritä kaksi mittaria viikkotarkastelua varten",
                "4. Sovi selkeä go/no-go -päätöspiste 2 viikon päähän",
                "5. Raportoi ohjausryhmälle etenemisestä viikoittain",
            ],
        }
