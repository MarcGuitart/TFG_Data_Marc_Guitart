#!/bin/bash
# AP2 Quick Test Script

echo "🎯 AP2 Selector Adaptativo - Quick Test"
echo "========================================"
echo ""

# Test 1: Upload test data via frontend
echo "📤 Step 1: Upload test CSV..."
echo "   Go to: http://localhost:5173"
echo "   Upload: data/ap1_test_data.csv"
echo "   Click: 🚀 Ejecutar agente"
echo ""
read -p "Press ENTER after executing pipeline..."

# Test 2: Wait for agent processing
echo ""
echo "⏳ Step 2: Waiting for agent processing (10 seconds)..."
sleep 10

# Test 3: Check agent logs for chosen model
echo ""
echo "🔍 Step 3: Checking agent logs for 'chosen' field..."
CHOSEN_COUNT=$(docker logs docker-agent-1 --tail 50 2>&1 | grep -c "chosen=" || echo "0")
if [ "$CHOSEN_COUNT" -gt 0 ]; then
    echo "✅ Found $CHOSEN_COUNT predictions with chosen model!"
    echo ""
    echo "Sample logs:"
    docker logs docker-agent-1 --tail 50 2>&1 | grep "chosen=" | tail -5
else
    echo "❌ No 'chosen' field found in logs"
    echo "   Agent might not be in adaptive mode or no data processed yet"
fi

# Test 4: Check InfluxDB for chosen_model measurement
echo ""
echo "🗄️  Step 4: Checking InfluxDB for chosen_model data..."
INFLUX_RESULT=$(docker exec docker-influxdb-1 influx query \
  'from(bucket:"pipeline") 
   |> range(start:-1h) 
   |> filter(fn:(r)=> r._measurement=="chosen_model") 
   |> count()' \
  -o tfg -t admin_token 2>&1 | grep -c "chosen_model" || echo "0")

if [ "$INFLUX_RESULT" -gt 0 ]; then
    echo "✅ Found chosen_model data in InfluxDB!"
    echo ""
    echo "Sample data:"
    docker exec docker-influxdb-1 influx query \
      'from(bucket:"pipeline") 
       |> range(start:-1h) 
       |> filter(fn:(r)=> r._measurement=="chosen_model") 
       |> limit(n:5)' \
      -o tfg -t admin_token 2>&1 | grep -E "(_value:|_time:)" | head -10
else
    echo "❌ No chosen_model data in InfluxDB"
fi

# Test 5: Check backend endpoint
echo ""
echo "🌐 Step 5: Testing backend /api/series endpoint..."
RESPONSE=$(curl -s "http://localhost:8081/api/series?id=TestSeries&hours=1" 2>/dev/null || echo "{}")
CHOSEN_COUNT=$(echo "$RESPONSE" | python3 -c "import json, sys; d=json.load(sys.stdin); print(len(d.get('chosen_models', [])))" 2>/dev/null || echo "0")

if [ "$CHOSEN_COUNT" -gt 0 ]; then
    echo "✅ Backend returns $CHOSEN_COUNT chosen_models entries!"
    echo ""
    echo "Sample chosen_models:"
    echo "$RESPONSE" | python3 -c "import json, sys; d=json.load(sys.stdin); [print(f'{c[\"t\"]}: {c[\"model\"]}') for c in d.get('chosen_models', [])[:5]]" 2>/dev/null
else
    echo "❌ Backend returns 0 chosen_models"
    echo "   Check if ID 'TestSeries' exists or use 'Other'"
fi

# Test 6: Frontend check
echo ""
echo "🖥️  Step 6: Frontend visualization..."
echo "   Go to: http://localhost:5173"
echo "   Click: 'Load backend series (per-model)'"
echo "   Look for: '🎯 Selector Adaptativo - Modelo Elegido por Instante' table"
echo ""

# Summary
echo "========================================"
echo "📊 Summary:"
echo "   Agent logs with chosen: $CHOSEN_COUNT"
echo "   InfluxDB has data: $([ "$INFLUX_RESULT" -gt 0 ] && echo 'YES' || echo 'NO')"
echo "   Backend returns chosen: $CHOSEN_COUNT models"
echo ""
echo "✅ AP2 Implementation: $([ "$CHOSEN_COUNT" -gt 0 ] && echo 'WORKING' || echo 'NEEDS DEBUGGING')"
echo ""
echo "📸 Next: Take screenshots for tutor!"
echo "   1. Agent logs with 'chosen=' field"
echo "   2. Frontend table of chosen models"
echo "   3. InfluxDB query showing chosen_model measurement"
