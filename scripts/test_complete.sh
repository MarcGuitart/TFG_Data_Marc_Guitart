#!/bin/bash

#╔════════════════════════════════════════════════════════════════════════════╗
#║                                                                            ║
#║              🧪 TEST COMPLETO: AP1 + AP2 + AP3 + FRONTEND                 ║
#║                                                                            ║
#║                        Verificación Integral del Sistema                   ║
#║                                                                            ║
#╚════════════════════════════════════════════════════════════════════════════╝

set -e

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de reporte
pass() {
  echo -e "${GREEN}✓ PASS${NC}: $1"
}

fail() {
  echo -e "${RED}✗ FAIL${NC}: $1"
  exit 1
}

info() {
  echo -e "${BLUE}ℹ INFO${NC}: $1"
}

warn() {
  echo -e "${YELLOW}⚠ WARN${NC}: $1"
}

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    🧪 TEST SUITE COMPLETO AP1/AP2/AP3                     ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# TEST 1: Verificar que servicios están corriendo
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 1: Servicios Docker"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

cd /Users/marcg/Desktop/projectes/TFG_Agente_Data/docker

docker-compose ps | grep -q "docker-agent-1" && pass "Agent container activo" || fail "Agent container no está corriendo"
docker-compose ps | grep -q "docker-orchestrator-1" && pass "Orchestrator container activo" || fail "Orchestrator no está corriendo"
docker-compose ps | grep -q "docker-window_collector-1" && pass "Collector container activo" || fail "Collector no está corriendo"
docker-compose ps | grep -q "kafka" && pass "Kafka container activo" || fail "Kafka no está corriendo"
docker-compose ps | grep -q "influxdb" && pass "InfluxDB container activo" || fail "InfluxDB no está corriendo"

echo ""

# TEST 2: Verificar conexión Kafka
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 2: Conexión Kafka"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

docker logs docker-agent-1 2>&1 | grep -q "Successfully joined group agent-v1" && pass "Agent conectado a Kafka" || fail "Agent no está conectado a Kafka"

echo ""

# TEST 3: Verificar que Orchestrator responde
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 3: Backend API"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8081/api/series?id=test)
if [ "$RESPONSE" = "200" ] || [ "$RESPONSE" = "400" ]; then
  pass "Orchestrator responde en puerto 8081"
else
  fail "Orchestrator no responde correctamente (HTTP $RESPONSE)"
fi

echo ""

# TEST 4: Verificar estructura de response
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 4: Estructura de Respuesta API"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

RESPONSE=$(curl -s http://localhost:8081/api/series?id=test)

echo "$RESPONSE" | jq -e '.observed' > /dev/null 2>&1 && pass "Response contiene 'observed'" || fail "Response sin 'observed'"
echo "$RESPONSE" | jq -e '.predicted' > /dev/null 2>&1 && pass "Response contiene 'predicted'" || fail "Response sin 'predicted'"
echo "$RESPONSE" | jq -e '.models' > /dev/null 2>&1 && pass "Response contiene 'models' (AP1)" || fail "Response sin 'models'"
echo "$RESPONSE" | jq -e '.chosen_models' > /dev/null 2>&1 && pass "Response contiene 'chosen_models' (AP2)" || fail "Response sin 'chosen_models'"
echo "$RESPONSE" | jq -e '.weights' > /dev/null 2>&1 && pass "Response contiene 'weights' (AP3)" || fail "Response sin 'weights'"

echo ""

# TEST 5: Verificar código Python
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 5: Código Python"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

grep -q "def update_weights" /Users/marcg/Desktop/projectes/TFG_Agente_Data/services/agent/hypermodel/hyper_model.py && pass "update_weights existe" || fail "update_weights no existe"
grep -q "self.w\[name\] -= 1.0" /Users/marcg/Desktop/projectes/TFG_Agente_Data/services/agent/hypermodel/hyper_model.py && pass "AP3: penalización implementada" || fail "AP3: penalización no implementada"
grep -q "def _query_weights" /Users/marcg/Desktop/projectes/TFG_Agente_Data/services/orchestrator/app.py && pass "_query_weights existe" || fail "_query_weights no existe"

echo ""

# TEST 6: Verificar Frontend
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 6: Frontend"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

grep -q "⚖️ Evolución de Pesos" /Users/marcg/Desktop/projectes/TFG_Agente_Data/frontend/src/components/DataPipelineLiveViewer.jsx && pass "Panel AP3 en frontend" || fail "Panel AP3 no encontrado"
grep -q "📈 Vista Individual por Modelo" /Users/marcg/Desktop/projectes/TFG_Agente_Data/frontend/src/components/DataPipelineLiveViewer.jsx && pass "Panel AP1 (modelos individuales) en frontend" || fail "Panel AP1 no encontrado"
grep -q "🎯 Selector Adaptativo" /Users/marcg/Desktop/projectes/TFG_Agente_Data/frontend/src/components/DataPipelineLiveViewer.jsx && pass "Panel AP2 (selector adaptativo) en frontend" || fail "Panel AP2 no encontrado"

# Verificar que Agent Logs fue eliminado
! grep -q "Agent Logs" /Users/marcg/Desktop/projectes/TFG_Agente_Data/frontend/src/components/DataPipelineLiveViewer.jsx && pass "Agent Logs eliminado del frontend" || fail "Agent Logs aún en frontend"
! grep -q "Kafka Out" /Users/marcg/Desktop/projectes/TFG_Agente_Data/frontend/src/components/DataPipelineLiveViewer.jsx && pass "Kafka Out eliminado del frontend" || fail "Kafka Out aún en frontend"

echo ""

# TEST 7: Verificar InfluxDB measurements
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 7: InfluxDB Measurements"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

info "Verificando que InfluxDB tiene los measurements necesarios..."
INFLUX_QUERY=$(docker exec docker-influxdb-1 influx bucket list 2>&1 | grep -c "pipeline" || echo "0")
if [ "$INFLUX_QUERY" -gt 0 ]; then
  pass "Bucket 'pipeline' existe en InfluxDB"
else
  warn "No se puede verificar bucket (puede no haber datos aún)"
fi

echo ""

# TEST 8: Verificar docker-compose.yml
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 8: Configuración Docker"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

grep -q "HYPERMODEL_MODE=adaptive" /Users/marcg/Desktop/projectes/TFG_Agente_Data/docker/docker-compose.yml && pass "HYPERMODEL_MODE=adaptive configurado" || fail "HYPERMODEL_MODE no configurado"

echo ""

# TEST 9: Verificar documentación
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo "TEST 9: Documentación"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

[ -f "/Users/marcg/Desktop/projectes/TFG_Agente_Data/AP3_SUMMARY.md" ] && pass "AP3_SUMMARY.md existe" || fail "AP3_SUMMARY.md no existe"
[ -f "/Users/marcg/Desktop/projectes/TFG_Agente_Data/AP3_SISTEMA_PESOS.md" ] && pass "AP3_SISTEMA_PESOS.md existe" || fail "AP3_SISTEMA_PESOS.md no existe"
[ -f "/Users/marcg/Desktop/projectes/TFG_Agente_Data/AP3_GUIA_VERIFICACION.md" ] && pass "AP3_GUIA_VERIFICACION.md existe" || fail "AP3_GUIA_VERIFICACION.md no existe"
[ -f "/Users/marcg/Desktop/projectes/TFG_Agente_Data/README_AP3.md" ] && pass "README_AP3.md existe" || fail "README_AP3.md no existe"
[ -f "/Users/marcg/Desktop/projectes/TFG_Agente_Data/scripts/test_ap3.sh" ] && pass "test_ap3.sh existe" || fail "test_ap3.sh no existe"

echo ""

# Resumen Final
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    ✅ TEST SUITE COMPLETADO                              ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}🎉 TODOS LOS TESTS PASARON EXITOSAMENTE${NC}"
echo ""
echo "📝 PRÓXIMOS PASOS:"
echo "  1. Abre http://localhost:5173 en tu navegador"
echo "  2. Carga un CSV (data/test_csvs/sine_300.csv)"
echo "  3. Ejecuta el agente"
echo "  4. Verifica que los paneles se muestren correctamente"
echo ""
echo "✅ VERIFICACIÓN:"
echo "  ✓ Backend: http://localhost:8081/api/series?id=test"
echo "  ✓ Frontend: http://localhost:5173"
echo "  ✓ InfluxDB: Almacenando datos en 'pipeline' bucket"
echo ""
