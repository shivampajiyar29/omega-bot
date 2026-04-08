import asyncio
import os
import sys
from unittest.mock import MagicMock

# --- Mocking missing dependencies to allow imports ---
try:
    import pydantic_settings
except ImportError:
    # Create a mock for pydantic-settings
    m = MagicMock()
    m.BaseSettings = MagicMock
    sys.modules["pydantic_settings"] = m

try:
    import ccxt
except ImportError:
    sys.modules["ccxt"] = MagicMock()

# Add the apps/api directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "apps", "api"))

async def quick_verify():
    print("--- Quick Verification (Post-Merge) ---")
    
    # 1. Check Registry Registration
    try:
        from app.connectors.registry import get_broker_adapter_class
        binance_cls = get_broker_adapter_class("binance")
        mock_cls = get_broker_adapter_class("mock")
        print(f"Registry: Binance adapter class found -> {binance_cls}")
        print(f"Registry: Mock adapter class found -> {mock_cls}")
    except Exception as e:
        print(f"Registry Check: FAILED - {e}")

    # 2. Check Adapter Class Existence and Imports
    try:
        from app.adapters.broker.binance import BinanceBrokerAdapter
        from app.adapters.broker.mock_broker import MockBrokerAdapter
        print("Adapter Imports: SUCCESS")
    except ImportError as e:
        print(f"Adapter Imports: FAILED - {e}")

    # 3. Check Celery Agent Entry Point
    celery_path = "apps/worker/celery_app.py"
    if os.path.exists(celery_path):
        print(f"Agent Check: {celery_path} exists.")
    else:
        print(f"Agent Check: FAILED - {celery_path} missing.")

if __name__ == "__main__":
    asyncio.run(quick_verify())
