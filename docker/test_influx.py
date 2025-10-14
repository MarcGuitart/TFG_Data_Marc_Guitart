from influxdb_client import InfluxDBClient
import os

# --- Configuración de conexión ---
url = os.getenv("INFLUX_URL", "http://localhost:8086")
token = os.getenv("INFLUX_TOKEN", "admin_token")
org = os.getenv("INFLUX_ORG", "tfg")
bucket = os.getenv("INFLUX_BUCKET", "pipeline")

client = InfluxDBClient(url=url, token=token, org=org)

print("✅ Conectado a InfluxDB")

# --- Consulta Flux ---
query = f'''
from(bucket:"{bucket}")
    |> range(start: -6h)
    |> filter(fn: (r) => r._measurement == "telemetry")
    |> limit(n: 10)
'''

# --- Ejecución ---
tables = client.query_api().query(query, org=org)

# --- Resultados ---
found = False
for table in tables:
    for record in table.records:
        print(record.values)
        found = True

if not found:
    print("⚠️ No se encontraron registros en el bucket 'pipeline'")
