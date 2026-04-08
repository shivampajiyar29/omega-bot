import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the apps/api directory to sys.path so we can import 'app'
sys.path.append(os.path.join(os.getcwd(), "apps", "api"))

load_dotenv(".env")

async def verify_adapters():
    print("--- Verifying Broker Adapters ---")
    
    try:
        from app.adapters.broker.binance import BinanceBrokerAdapter
        from app.adapters.broker.mock_broker import MockBrokerAdapter
        print("Import Status: SUCCESS")
    except ImportError as e:
        print(f"Import Status: FAILED - {e}")
        return

    # Test Mock Broker
    try:
        mock = MockBrokerAdapter(config={"initial_balance": 10000})
        await mock.connect()
        acc = await mock.get_account()
        print(f"Mock Broker Connect: SUCCESS (Balance: {acc.get('cash')})")
        await mock.disconnect()
    except Exception as e:
        print(f"Mock Broker Test: FAILED - {e}")

    # Test Binance Broker (Connectivity only)
    try:
        binance = BinanceBrokerAdapter()
        # We don't want to wait forever if it hangs
        success = await asyncio.wait_for(binance.connect(), timeout=10)
        if success:
            print("Binance Adapter Connect: SUCCESS")
            # Try to get a quote to verify live market data
            quote = await binance.get_quote("BTCUSDT")
            if quote:
                 print(f"Binance Live Market (BTCUSDT): {quote.get('ltp')}")
            else:
                 print("Binance Live Market: FAILED (No quote)")
        else:
            print("Binance Adapter Connect: FAILED")
        await binance.disconnect()
    except asyncio.TimeoutError:
        print("Binance Adapter Connect: FAILED (Timeout - Check API Keys/IP Allowlist)")
    except Exception as e:
        print(f"Binance Adapter Test: FAILED - {e}")

if __name__ == "__main__":
    asyncio.run(verify_adapters())
