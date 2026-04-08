"""
Multi-Provider AI Assistant
Priority: Gemini → NVIDIA NIM → OpenRouter → Anthropic → OpenAI

Supports:
- Strategy generation from natural language
- Backtest result analysis
- Custom indicator creation (Python code)
- Risk assessment
- Trade journal analysis
"""
from __future__ import annotations
import json
import logging
from typing import Optional, List, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

STRATEGY_SYSTEM = """You are an expert quantitative trading strategy assistant for OmegaBot.
Generate strategies as valid JSON DSL. Respond ONLY with the JSON when asked to generate.

DSL schema:
{
  "version": "1.0", "name": "string", "description": "string",
  "market_types": ["equity"|"futures"|"crypto"|"forex"],
  "timeframe": "1m|5m|15m|30m|1h|4h|1d",
  "indicators": [{"id": "unique_id", "type": "ema|sma|rsi|macd|bbands|atr|vwap", "params": {"period": number}}],
  "entry": {"long": {"logic": "and|or", "conditions": [{"left": {"indicator_id": "id"}, "operator": "gt|gte|lt|lte|crosses_above|crosses_below", "right": {"value": number}}]}},
  "exits": [{"type": "fixed_stop|fixed_target|trailing_stop|indicator_signal", "value": number, "unit": "pct|points"}],
  "sizing": {"method": "fixed_value|pct_capital|fixed_qty|risk_pct", "value": number},
  "allow_short": false
}

Rules: Only supported indicators. Never bypass risk controls. Be practical and testable."""

INDICATOR_SYSTEM = """You are an expert at writing Python technical analysis indicator code for OmegaBot.
When asked to create a custom indicator:
1. Write clean, working Python code using pandas and numpy only
2. Function signature: def compute(df: pd.DataFrame, **params) -> pd.Series
3. df has columns: open, high, low, close, volume (all float)
4. Return a pd.Series aligned to df index
5. Include docstring with parameter descriptions
6. Respond ONLY with the Python function code"""

CHAT_SYSTEM = """You are OmegaBot AI — an expert trading assistant.
Help with: strategy creation, backtest analysis, risk metrics, indicator design, trade psychology.
Available AI: Google Gemini, NVIDIA NIM, custom indicators, backtesting.
Be direct, practical, and risk-aware. Always mention position sizing and stops."""


async def call_ai(
    system_prompt: str,
    messages: List[Dict],
    max_tokens: int = 1500,
    temperature: float = 0.3,
) -> str:
    """
    Call the best available AI provider.
    Priority: Gemini > NVIDIA > OpenRouter > Anthropic > OpenAI
    """
    provider = settings.AI_PROVIDER.lower()

    # Try configured provider first, then cascade
    providers = [provider] + [p for p in ["gemini", "nvidia", "openrouter", "anthropic", "openai"] if p != provider]

    for p in providers:
        try:
            result = await _call_provider(p, system_prompt, messages, max_tokens, temperature)
            if result:
                return result
        except Exception as e:
            logger.debug(f"AI provider {p} failed: {e}, trying next...")
            continue

    return "No AI provider available. Add GEMINI_API_KEY, NVIDIA_API_KEY, or OPENROUTER_API_KEY to .env"


async def _call_provider(provider: str, system: str, messages: List[Dict], max_tokens: int, temperature: float) -> Optional[str]:
    if provider == "gemini" and settings.GEMINI_API_KEY:
        return await _call_gemini(system, messages, max_tokens, temperature)
    elif provider == "nvidia" and settings.NVIDIA_API_KEY:
        return await _call_nvidia(system, messages, max_tokens, temperature)
    elif provider == "openrouter" and settings.OPENROUTER_API_KEY:
        return await _call_openrouter(system, messages, max_tokens, temperature)
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return await _call_anthropic(system, messages, max_tokens)
    elif provider == "openai" and settings.OPENAI_API_KEY:
        return await _call_openai(system, messages, max_tokens, temperature)
    return None


async def _call_gemini(system: str, messages: List[Dict], max_tokens: int, temperature: float) -> str:
    """Google Gemini Pro via REST API."""
    import httpx

    combined_content = system + "\n\n"
    for m in messages:
        role = "User" if m["role"] == "user" else "Assistant"
        combined_content += f"{role}: {m['content']}\n"
    combined_content += "Assistant:"

    payload = {
        "contents": [{"parts": [{"text": combined_content}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature": temperature,
        },
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_nvidia(system: str, messages: List[Dict], max_tokens: int, temperature: float) -> str:
    """NVIDIA NIM API — great for code and quant tasks."""
    import httpx

    all_messages = [{"role": "system", "content": system}] + messages

    payload = {
        "model":       "meta/llama-3.1-70b-instruct",
        "messages":    all_messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
        "stream":      False,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.NVIDIA_BASE_URL}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.NVIDIA_API_KEY}",
                "Content-Type":  "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_openrouter(system: str, messages: List[Dict], max_tokens: int, temperature: float) -> str:
    """OpenRouter — access to Grok, Mistral, etc."""
    import httpx

    all_messages = [{"role": "system", "content": system}] + messages

    payload = {
        "model":       "mistralai/mistral-7b-instruct",  # fast + free tier
        "messages":    all_messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://omegabot.local",
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_anthropic(system: str, messages: List[Dict], max_tokens: int) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def _call_openai(system: str, messages: List[Dict], max_tokens: int, temperature: float) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content


# ─── Public API ───────────────────────────────────────────────────────────────

async def generate_strategy_from_description(description: str, market_type: str = "equity", timeframe: str = "15m") -> Dict:
    """Generate a complete strategy DSL from plain English."""
    prompt = f"""Generate a trading strategy for: "{description}"
Market: {market_type} | Timeframe: {timeframe}
Respond ONLY with valid JSON, no markdown, no explanation."""

    raw = await call_ai(
        system_prompt=STRATEGY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1200,
        temperature=0.2,
    )

    # Strip markdown fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    dsl = json.loads(raw)

    # Validate through DSL schema
    from app.strategy.dsl import StrategyDSL
    validated = StrategyDSL(**dsl)

    return {"strategy": dsl, "valid": True, "provider": settings.AI_PROVIDER}


async def generate_custom_indicator_code(description: str, params: Dict = None) -> Dict:
    """
    Generate Python code for a custom indicator from plain English.
    Returns executable Python function code.
    """
    prompt = f"""Create a Python technical indicator function for: "{description}"
Parameters needed: {json.dumps(params or {})}
Return ONLY the Python function code starting with 'def compute('"""

    code = await call_ai(
        system_prompt=INDICATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.1,
    )

    # Clean code block markers
    code = code.strip()
    if code.startswith("```python"):
        code = code[9:]
    if code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]

    return {"code": code.strip(), "provider": settings.AI_PROVIDER}


async def analyze_backtest_results(results: Dict) -> str:
    """Analyze backtest results and provide actionable insights."""
    prompt = f"""Analyze these backtest results and give me a direct, actionable assessment (150 words max):

{json.dumps({k: v for k, v in results.items() if k not in ('equity_curve', 'trade_log', 'monthly_returns')}, indent=2)}

Cover: viability, key risks, one concrete improvement."""

    return await call_ai(
        system_prompt=CHAT_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.4,
    )


async def chat(message: str, history: List[Dict] = None) -> str:
    """General trading assistant chat."""
    messages = (history or []) + [{"role": "user", "content": message}]
    return await call_ai(
        system_prompt=CHAT_SYSTEM,
        messages=messages,
        max_tokens=600,
        temperature=0.5,
    )
