import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import redis.asyncio as redis
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync

load_dotenv("../../.env")

async def test_db():
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    
    redis_url = os.getenv("REDIS_URL")

    try:
        print("Testing Postgres...")
        if not db_url:
            print("No DATABASE_URL found.")
        else:
            conn = await asyncpg.connect(db_url)
            print("Postgres Connection: SUCCESS")
            await conn.close()
    except Exception as e:
        print(f"Postgres Connection: FAILED - {e}")

    try:
        print("Testing Redis...")
        if not redis_url:
            print("No REDIS_URL found.")
        else:
            r = await redis.from_url(redis_url)
            await r.ping()
            print("Redis Connection: SUCCESS")
            await r.aclose()
    except Exception as e:
        print(f"Redis Connection: FAILED - {e}")

    try:
        print("Testing InfluxDB...")
        influx_url = os.getenv("INFLUXDB_URL")
        influx_token = os.getenv("INFLUXDB_TOKEN")
        influx_org = os.getenv("INFLUXDB_ORG")
        
        client = InfluxDBClientAsync(url=influx_url, token=influx_token, org=influx_org)
        ping_res = await client.ping()
        if ping_res:
             print("InfluxDB Connection: SUCCESS")
        else:
             print("InfluxDB Connection: Unknown Ping Result")
        await client.close()
    except Exception as e:
        print(f"InfluxDB Connection: FAILED - {e}")

asyncio.run(test_db())
