import os
import json
import asyncio
import asyncpg
from fastapi import FastAPI, BackgroundTasks
import paho.mqtt.client as mqtt
from pydantic import BaseModel

app = FastAPI(title="SmartPath IoT Service")

# TimescaleDB / PostgreSQL Config
DB_USER = os.getenv("PGUSER", "smartpath")
DB_PASS = os.getenv("PGPASSWORD", "smartpath123")
DB_HOST = os.getenv("PGHOST", "timescaledb")
DB_NAME = os.getenv("PGDATABASE", "smartpath_iot")
DB_PORT = os.getenv("PGPORT", "5432")

# MQTT Config
MQTT_BROKER = os.getenv('MQTT_BROKER', 'rabbitmq')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
MQTT_TOPIC_TELEMETRY = "smartpath/iot/telemetry"

pool = None

async def init_db():
    global pool
    try:
        pool = await asyncpg.create_pool(
            user=DB_USER, password=DB_PASS, database=DB_NAME, host=DB_HOST, port=DB_PORT
        )
        
        async with pool.acquire() as conn:
            # Setup TimescaleDB extension and hypertable
            await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sensor_data (
                    time TIMESTAMPTZ NOT NULL,
                    device_id VARCHAR(50) NOT NULL,
                    sensor_type VARCHAR(50) NOT NULL,
                    value DOUBLE PRECISION NOT NULL
                );
            """)
            
            # Make it a hypertable if it isn't already
            try:
                await conn.execute("SELECT create_hypertable('sensor_data', 'time', if_not_exists => TRUE);")
            except Exception:
                pass
                
    except Exception as e:
        print(f"Failed to connect to TimescaleDB: {e}")

@app.on_event("startup")
async def startup_event():
    await init_db()
    
    # Start MQTT Client in a background thread managed by paho
    client = mqtt.Client(client_id="IoTService")
    client.on_message = on_mqtt_message
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.subscribe(MQTT_TOPIC_TELEMETRY)
        client.loop_start()
        print(f"MQTT Connected to {MQTT_BROKER}:{MQTT_PORT}")
    except Exception as e:
        print(f"MQTT Connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    if pool:
        await pool.close()

def on_mqtt_message(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode('utf-8'))
        device_id = payload.get("device_id")
        sensor_type = payload.get("sensor_type")
        value = payload.get("value")
        
        if device_id and sensor_type and value is not None:
            # We must use asyncio.run or create a task since this callback is synchronous
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(insert_telemetry(device_id, sensor_type, value))
            else:
                loop.run_until_complete(insert_telemetry(device_id, sensor_type, value))
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

async def insert_telemetry(device_id: str, sensor_type: str, value: float):
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO sensor_data (time, device_id, sensor_type, value) VALUES (NOW(), $1, $2, $3)",
                device_id, sensor_type, float(value)
            )

class TelemetryPayload(BaseModel):
    device_id: str
    sensor_type: str
    value: float

@app.post("/telemetry")
async def post_telemetry(payload: TelemetryPayload):
    """Fallback HTTP endpoint for devices that cannot use MQTT"""
    await insert_telemetry(payload.device_id, payload.sensor_type, payload.value)
    return {"status": "recorded"}

@app.get("/health")
def health_check():
    return {"status": "UP"}
