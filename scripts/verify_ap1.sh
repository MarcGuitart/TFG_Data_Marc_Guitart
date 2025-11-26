#!/bin/bash
# AP1 Verification Script
# Tests per-model prediction visualization

set -e

echo "🔍 AP1 Per-Model Predictions Verification"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check Docker Containers
echo "1️⃣  Checking Docker containers..."
if docker ps --format "{{.Names}}" | grep -q "docker-agent-1"; then
    echo -e "${GREEN}✓${NC} Agent running"
else
    echo -e "${RED}✗${NC} Agent not running"
    exit 1
fi

if docker ps --format "{{.Names}}" | grep -q "docker-orchestrator-1"; then
    echo -e "${GREEN}✓${NC} Orchestrator running"
else
    echo -e "${RED}✗${NC} Orchestrator not running"
    exit 1
fi

if docker ps --format "{{.Names}}" | grep -q "docker-window_collector-1"; then
    echo -e "${GREEN}✓${NC} Collector running"
else
    echo -e "${RED}✗${NC} Collector not running"
    exit 1
fi
echo ""

# 2. Check Agent is generating predictions
echo "2️⃣  Checking agent predictions..."
PRED_COUNT=$(docker logs docker-agent-1 --tail 100 2>&1 | grep -c "\[pred\]" || echo "0")
if [ "$PRED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Agent has generated $PRED_COUNT predictions"
    docker logs docker-agent-1 --tail 5 2>&1 | grep "\[pred\]" | tail -1
else
    echo -e "${YELLOW}⚠${NC}  No predictions found in agent logs (might need to run pipeline)"
fi
echo ""

# 3. Check InfluxDB for per-model data
echo "3️⃣  Checking InfluxDB for per-model data..."
MODEL_COUNT=$(docker exec docker-influxdb-1 influx query \
  'from(bucket:"pipeline") |> range(start:-24h) |> filter(fn:(r)=> r._measurement=="telemetry_models") |> count()' \
  -o tfg -t admin_token 2>/dev/null | grep -c "telemetry_models" || echo "0")

if [ "$MODEL_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found per-model data in InfluxDB"
    echo "Sample data:"
    docker exec docker-influxdb-1 influx query \
      'from(bucket:"pipeline") |> range(start:-1h) |> filter(fn:(r)=> r._measurement=="telemetry_models") |> limit(n:3)' \
      -o tfg -t admin_token 2>&1 | grep -E "(id:|model:|_value:)" | head -9
else
    echo -e "${YELLOW}⚠${NC}  No per-model data found (might need to run pipeline)"
fi
echo ""

# 4. Test orchestrator endpoint
echo "4️⃣  Testing /api/series endpoint..."
RESPONSE=$(curl -s "http://localhost:8081/api/series?id=Other&hours=24" 2>/dev/null || echo "{}")
MODELS=$(echo "$RESPONSE" | python3 -c "import json, sys; d=json.load(sys.stdin); print(list(d.get('models', {}).keys()))" 2>/dev/null || echo "[]")
POINTS=$(echo "$RESPONSE" | python3 -c "import json, sys; d=json.load(sys.stdin); print(len(d.get('points', [])))" 2>/dev/null || echo "0")

if [ "$POINTS" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Endpoint returns $POINTS points with models: $MODELS"
    echo "Sample point:"
    echo "$RESPONSE" | python3 -c "import json, sys; d=json.load(sys.stdin); p=d.get('points', [None])[0]; print(json.dumps(p, indent=2))" 2>/dev/null || echo "{}"
else
    echo -e "${YELLOW}⚠${NC}  Endpoint returns 0 points (might need to run pipeline or check ID)"
fi
echo ""

# 5. Check frontend status
echo "5️⃣  Checking frontend..."
if lsof -ti:5173 > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend running on http://localhost:5173"
else
    echo -e "${RED}✗${NC} Frontend not running"
    echo "   Start with: cd frontend && npm run dev"
fi
echo ""

# Summary
echo "=========================================="
echo "📋 Summary:"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:5173"
echo "2. Upload a CSV file (e.g., data/sine_900.csv)"
echo "3. Click '🚀 Ejecutar agente'"
echo "4. Select ID from dropdown"
echo "5. Click 'Load backend series (per-model)'"
echo "6. Take screenshots for AP1 deliverable"
echo ""
echo "For more details, see: AP1_PER_MODEL_PREDICTIONS.md"
