"""
AI Assistant API — strategy generation and explanation via LLM.
Uses Anthropic Claude or OpenAI depending on configuration.
All AI output goes through DSL validation before being returned.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import json
import logging
import aiohttp

from app.core.config import settings
from app.strategy.dsl import StrategyDSL, SAMPLE_STRATEGIES

router = APIRouter()
logger = logging.getLogger(__name__)

STRATEGY_SYSTEM_PROMPT = """You are an expert quantitative trading strategy assistant.
Your job is to help the user create, explain, and optimize algorithmic trading strategies.

When asked to generate a strategy, you MUST respond with a valid JSON object matching this DSL schema:
{
  "version": "1.0",
  "name": "string",
  "description": "string",
  "market_types": ["equity"|"futures"|"crypto"|"forex"],
  "timeframe": "1m|5m|15m|30m|1h|4h|1d",
  "indicators": [
    {"id": "unique_id", "type": "ema|sma|rsi|macd|bbands|atr|vwap", "params": {"period": number}}
  ],
  "entry": {
    "long": {
      "logic": "and|or",
      "conditions": [
        {
          "left": {"indicator_id": "id_from_indicators", "field": "optional_field"},
          "operator": "gt|gte|lt|lte|eq|neq|crosses_above|crosses_below",
          "right": {"indicator_id": "id_or_null", "value": number_or_null}
        }
      ]
    },
    "short": null  // only include if allow_short is true
  },
  "exits": [
    {"type": "fixed_stop", "value": 1.5, "unit": "pct"},
    {"type": "fixed_target", "value": 3.0, "unit": "pct"},
    {"type": "indicator_signal", "indicator_signal": { "logic": "and", "conditions": [...] }}
  ],
  "sizing": {"method": "fixed_value|fixed_qty|pct_capital|risk_pct", "value": number},
  "time_filter": {"start": "09:15", "end": "15:15"},
  "allow_short": false
}

Rules:
1. All indicator IDs in conditions must match IDs defined in the "indicators" array.
2. Only use supported indicator types: ema, sma, rsi, macd, bbands, atr, vwap, stoch, supertrend, price, volume.
3. For crossover conditions, use "crosses_above" or "crosses_below" operator.
4. For numeric thresholds, use the "value" field in the right ref (e.g., RSI < 30 → right: {"value": 30}).
5. Keep strategies practical and testable.
6. NEVER suggest bypassing risk controls.
7. Respond ONLY with the JSON object when asked to generate a strategy. No markdown, no explanation text alongside it.
"""

CHAT_SYSTEM_PROMPT = """You are OmegaBot AI, an expert trading assistant embedded in a personal algorithmic trading platform.
Help the user with:
- Understanding how strategies work
- Reviewing backtest results
- Explaining risk metrics (Sharpe ratio, drawdown, win rate, etc.)
- Suggesting strategy improvements
- Explaining DSL schema and how to write conditions
- General trading concepts

Be concise and practical. The user is a trader, not a developer.
When discussing backtest metrics, be direct about what the numbers mean and whether the strategy looks viable.
Never recommend putting all capital in one trade. Always mention risk management.
"""


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None
    history: Optional[List[dict]] = None  # [{role, content}]


class GenerateStrategyRequest(BaseModel):
    description: str
    market_type: str = "equity"
    timeframe: str = "15m"


@router.post("/chat")
async def chat(req: ChatRequest):
    """General chat with the AI assistant."""
    if not settings.ai_enabled:
        return {"reply": _ai_disabled_message(), "source": "fallback"}

    history = req.history or []
    messages = history + [{"role": "user", "content": req.message}]

    if req.context:
        ctx_text = f"\n\nCurrent context:\n{json.dumps(req.context, indent=2)}"
        messages[-1]["content"] += ctx_text

    try:
        reply = await _call_llm(CHAT_SYSTEM_PROMPT, messages)
        return {"reply": reply, "source": "ai"}
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")


@router.post("/generate-strategy")
async def generate_strategy(req: GenerateStrategyRequest):
    """
    Generate a strategy DSL from a plain English description.
    The generated DSL is validated before being returned.
    """
    if not settings.ai_enabled:
        # Return a sample strategy as fallback
        return {
            "strategy": SAMPLE_STRATEGIES["ema_crossover"],
            "explanation": "AI is not configured. Returning sample EMA Crossover strategy. "
                           "Add at least one provider key (Gemini/OpenAI/Anthropic/OpenRouter/NVIDIA) to .env.",
            "source": "fallback",
            "valid": True,
        }

    prompt = f"""Generate a trading strategy for: "{req.description}"
Market type: {req.market_type}
Timeframe: {req.timeframe}

Respond with ONLY the JSON strategy object. No markdown, no code blocks, no explanation."""

    try:
        raw = await _call_llm(STRATEGY_SYSTEM_PROMPT, [{"role": "user", "content": prompt}])

        # Strip any markdown code blocks the LLM might add
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        strategy_dict = json.loads(raw)

        # Validate through DSL schema
        validated = StrategyDSL(**strategy_dict)

        return {
            "strategy": strategy_dict,
            "explanation": f"Generated strategy: {strategy_dict.get('name', '')}. "
                           f"Review and adjust the parameters before running.",
            "source": "ai",
            "valid": True,
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"AI returned invalid JSON: {e}")
    except Exception as e:
        logger.error(f"Strategy generation error: {e}")
        raise HTTPException(status_code=503, detail=f"Generation failed: {e}")


@router.post("/explain-backtest")
async def explain_backtest(backtest_results: dict):
    """Explain backtest results in plain English."""
    if not settings.ai_enabled:
        return {"explanation": _explain_results_fallback(backtest_results)}

    prompt = f"""Analyze these backtest results and give me a concise, practical assessment:

{json.dumps(backtest_results, indent=2)}

Include:
1. Whether the strategy looks viable (be direct)
2. What the Sharpe ratio and max drawdown tell us
3. The biggest red flags (if any)
4. One concrete improvement suggestion

Keep it under 200 words."""

    reply = await _call_llm(CHAT_SYSTEM_PROMPT, [{"role": "user", "content": prompt}])
    return {"explanation": reply}


# ─── LLM Callers ──────────────────────────────────────────────────────────────

async def _call_llm(system: str, messages: List[dict]) -> str:
    provider = (settings.AI_PROVIDER or "").strip().lower()

    if provider == "gemini" and settings.GEMINI_API_KEY:
        return await _call_gemini(system, messages)
    if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return await _call_anthropic(system, messages)
    if provider == "openai" and settings.OPENAI_API_KEY:
        return await _call_openai_compatible(
            base_url="https://api.openai.com/v1",
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o-mini",
            system=system,
            messages=messages,
        )
    if provider == "openrouter" and settings.OPENROUTER_API_KEY:
        return await _call_openai_compatible(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model="openai/gpt-4o-mini",
            system=system,
            messages=messages,
        )
    if provider == "nvidia" and settings.NVIDIA_API_KEY:
        return await _call_openai_compatible(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
            model="meta/llama-3.1-70b-instruct",
            system=system,
            messages=messages,
        )

    if settings.GEMINI_API_KEY:
        return await _call_gemini(system, messages)
    if settings.OPENAI_API_KEY:
        return await _call_openai_compatible(
            base_url="https://api.openai.com/v1",
            api_key=settings.OPENAI_API_KEY,
            model="gpt-4o-mini",
            system=system,
            messages=messages,
        )
    if settings.ANTHROPIC_API_KEY:
        return await _call_anthropic(system, messages)
    if settings.OPENROUTER_API_KEY:
        return await _call_openai_compatible(
            base_url=settings.OPENROUTER_BASE_URL,
            api_key=settings.OPENROUTER_API_KEY,
            model="openai/gpt-4o-mini",
            system=system,
            messages=messages,
        )
    if settings.NVIDIA_API_KEY:
        return await _call_openai_compatible(
            base_url=settings.NVIDIA_BASE_URL,
            api_key=settings.NVIDIA_API_KEY,
            model="meta/llama-3.1-70b-instruct",
            system=system,
            messages=messages,
        )

    raise ValueError("No supported AI API key configured")


async def _call_gemini(system: str, messages: List[dict]) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    preferred = [
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
    ]
    available = []
    try:
        for m in genai.list_models():
            if "generateContent" in getattr(m, "supported_generation_methods", []):
                available.append(m.name.replace("models/", ""))
    except Exception:
        available = []

    chosen = next((m for m in preferred if m in available), None) or (available[0] if available else preferred[-1])
    model = genai.GenerativeModel(chosen)
    user_text = "\n\n".join(
        [m.get("content", "") for m in messages if m.get("role") != "system"]
    )
    prompt = f"{system}\n\n{user_text}".strip()
    response = await model.generate_content_async(prompt)
    return (response.text or "").strip()


async def _call_anthropic(system: str, messages: List[dict]) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def _call_openai_compatible(base_url: str, api_key: str, model: str, system: str, messages: List[dict]) -> str:
    all_msgs = [{"role": "system", "content": system}] + messages
    payload = {"model": model, "messages": all_msgs, "max_tokens": 1500}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=45)) as session:
        async with session.post(f"{base_url.rstrip('/')}/chat/completions", headers=headers, json=payload) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise ValueError(f"Provider error {resp.status}: {text[:300]}")
            data = json.loads(text)
            return data["choices"][0]["message"]["content"]


def _ai_disabled_message() -> str:
    return (
        "AI Assistant is not configured. Add at least one provider key "
        "(Gemini/OpenAI/Anthropic/OpenRouter/NVIDIA) to .env and restart."
    )


def _explain_results_fallback(results: dict) -> str:
    wr = results.get("win_rate_pct", 0)
    ret = results.get("total_return_pct", 0)
    dd = results.get("max_drawdown_pct", 0)
    sharpe = results.get("sharpe_ratio", 0)
    trades = results.get("total_trades", 0)

    assessment = "looks viable" if wr > 55 and ret > 10 and dd < 20 else "needs improvement"
    return (
        f"Strategy {assessment}. Win rate: {wr}%, total return: {ret}%, "
        f"max drawdown: {dd}%, Sharpe: {sharpe} over {trades} trades. "
        f"Enable the AI assistant for detailed analysis."
    )
