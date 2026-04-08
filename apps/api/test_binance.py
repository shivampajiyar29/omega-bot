import os
import asyncio
import aiohttp
import hmac
import hashlib
import time
from dotenv import load_dotenv

load_dotenv("../../.env")

async def test_binance():
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    base_url = "https://api.binance.com"

    if not api_key or not api_secret:
        print("Binance API credentials missing in .env")
        return

    print(f"Testing Binance API...")

    # Set timeout to 10 seconds
    timeout = aiohttp.ClientTimeout(total=10)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Test Ping
        try:
            async with session.get(f"{base_url}/api/v3/ping") as resp:
                if resp.status == 200:
                    print("Binance Ping: SUCCESS")
                else:
                    print(f"Binance Ping: FAILED (Status {resp.status})")
        except Exception as e:
            print(f"Binance Ping Error: {e}")

        # Test Account Info (Signed Request)
        try:
            timestamp = int(time.time() * 1000)
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            
            headers = {'X-MBX-APIKEY': api_key}
            url = f"{base_url}/api/v3/account?{query_string}&signature={signature}"
            
            async with session.get(url, headers=headers) as resp:
                data = await resp.json()
                if resp.status == 200:
                    print("Binance Account Connection: SUCCESS")
                else:
                    print(f"Binance Account Connection: FAILED - {data.get('msg', 'Unknown Error')}")
        except Exception as e:
            print(f"Binance Account Error: {e}")

        # Test Ticker Price (Live Market)
        try:
            async with session.get(f"{base_url}/api/v3/ticker/price?symbol=BTCUSDT") as resp:
                data = await resp.json()
                if resp.status == 200:
                    print(f"Live Market (BTCUSDT): {data['price']}")
                else:
                    print("Live Market Test: FAILED")
        except Exception as e:
            print(f"Live Market Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_binance())
