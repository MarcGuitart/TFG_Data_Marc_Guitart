#!/bin/bash
# ==========================================
#  MovieMate / TFG_Agente_Data System Check
# ==========================================

echo -e "\n🚀 Starting full system diagnostic...\n"

# --- 1. Check container status ---
echo "🧩 Checking running containers..."
docker compose ps

# --- 2. Health checks ---
echo -e "\n🩺 Checking service health...\n"
services=("zookeeper" "kafka" "docker-influxdb-1" "docker-agent-1" "docker-window_loader-1" "docker-window_collector-1" "docker-orchestrator-1")
for s in "${services[@]}"; do
  if docker inspect --format '{{.State.Health.Status}}' "$s" 2>/dev/null | grep -q "healthy"; then
    echo "✅ $s healthy"
  else
    echo "⚠️  $s not healthy or no healthcheck defined"
  fi
done

# --- 3. Check Kafka connection ---
echo -e "\n🧠 Checking Kafka connectivity from agent..."
docker compose exec agent nc -zv kafka 9092
if [ $? -eq 0 ]; then
  echo "✅ Kafka reachable"
else
  echo "❌ Kafka connection failed"
fi

# --- 4. Check InfluxDB connectivity ---
echo -e "\n📊 Checking InfluxDB connectivity from agent..."
docker compose exec -T agent python3 - <<'EOF'
from influxdb_client import InfluxDBClient
try:
    c = InfluxDBClient(url="http://influxdb:8086", token="admin_token", org="tfg")
    buckets = [b.name for b in c.buckets_api().find_buckets().buckets]
    print("✅ Connected to InfluxDB. Buckets:", buckets)
except Exception as e:
    print("❌ InfluxDB connection failed:", e)
EOF

# --- 5. Check data pipeline ---
echo -e "\n📦 Triggering end-to-end data flow test..."
curl -s -X POST http://localhost:8082/reset | jq
curl -s -X POST http://localhost:8081/api/upload_csv -F "file=@../data/dades_traffic.csv"
curl -s -X POST http://localhost:8081/api/run_window | jq
sleep 3
curl -s http://localhost:8082/flush | jq

# --- 6. Verify data in InfluxDB ---
echo -e "\n🔍 Verifying data presence in InfluxDB..."
docker compose exec -T agent python3 - <<'EOF'
from influxdb_client import InfluxDBClient
c = InfluxDBClient(url="http://influxdb:8086", token="admin_token", org="tfg")
query = 'from(bucket:"pipeline") |> range(start:-6h) |> limit(n:5)'
tables = c.query_api().query(query, org="tfg")
count = 0
for t in tables:
    for r in t.records:
        count += 1
        print(r.values)
print(f"✅ {count} records fetched from InfluxDB." if count else "⚠️ No data found in InfluxDB.")
EOF

echo -e "\n✅ System check completed.\n"
