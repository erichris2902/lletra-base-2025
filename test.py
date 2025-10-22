import redis
import os

r = redis.from_url(os.environ.get("REDISCLOUD_URL", "redis://localhost:6379/0"))

try:
    r.ping()
    print("✅ Conexión exitosa a Redis")
except Exception as e:
    print("❌ Error al conectar:", e)