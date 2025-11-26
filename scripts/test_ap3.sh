#!/bin/bash

echo "🎯 Prueba completa de AP3: Sistema de Pesos por Modelo"
echo "======================================================"
echo ""

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}📋 REQUISITOS:${NC}"
echo "✓ Frontend en http://localhost:5173"
echo "✓ Backend en http://localhost:8081"
echo "✓ InfluxDB en http://localhost:8086"
echo ""

echo -e "${BLUE}📌 PASO 1: Verificar que Kafka está listo${NC}"
docker logs docker-agent-1 2>&1 | grep "Successfully joined group" > /dev/null && echo -e "${GREEN}✓ Agent conectado a Kafka${NC}" || echo -e "${YELLOW}⏳ Agent aún conectando...${NC}"
echo ""

echo -e "${BLUE}📌 PASO 2: Usar el Frontend${NC}"
echo "1. Abre http://localhost:5173"
echo "2. Click en '📂 Cargar CSV'"
echo "3. Selecciona: data/test_csvs/sine_300.csv"
echo "4. Click en '🚀 Ejecutar agente'"
echo "5. Espera 15-20 segundos"
echo ""

echo -e "${BLUE}📌 PASO 3: Verificar que el agente procesa datos${NC}"
echo "Comando a ejecutar:"
echo "  docker logs docker-agent-1 --tail 50 | grep '\\[pred\\]' | head -10"
echo ""

echo -e "${BLUE}📌 PASO 4: Verificar que pesos se guardan en InfluxDB${NC}"
echo "Query (en InfluxDB UI o CLI):"
echo "  from(bucket:\"pipeline\")"
echo "  |> range(start:-24h)"
echo "  |> filter(fn:(r)=> r._measurement==\"weights\")"
echo "  |> filter(fn:(r)=> r.id==\"TestSeries\")"
echo ""

echo -e "${BLUE}📌 PASO 5: Ver en Frontend${NC}"
echo "1. En http://localhost:5173"
echo "2. En panel 'Predicción'"
echo "3. Selecciona el ID (TestSeries o similar)"
echo "4. Click '📊 Cargar Series'"
echo "5. Scroll down hasta '⚖️ Evolución de Pesos (AP3)'"
echo "   - Verás un gráfico con evolución de pesos"
echo "   - Debajo, tabla con últimos pesos de cada modelo"
echo ""

echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}¿Qué esperar de AP3?${NC}"
echo "════════════════════════════════════════════"
echo ""
echo "📈 Gráfico de Evolución:"
echo "  - Línea por cada modelo (colors diferenciados)"
echo "  - Eje Y: Peso acumulado"
echo "  - Eje X: Tiempo"
echo "  - Puede ser creciente, decreciente, o negativo"
echo ""

echo "📊 Tabla de Últimos Pesos:"
echo "  - linear_8: X.X"
echo "  - poly2_12: X.X"  
echo "  - ab_fast: X.X"
echo ""

echo "🎓 Interpretación:"
echo "  - Peso ALTO (+50): Modelo funciona bien"
echo "  - Peso BAJO (-10): Modelo falla consistentemente"
echo "  - DIFERENCIA clara: Sistema de ranking trabaja"
echo ""

echo -e "${YELLOW}⚠️ NOTA:${NC}"
echo "Si no ves datos:"
echo "  1. Verifica que 'TestSeries' aparece en el dropdown"
echo "  2. Ejecuta: docker logs docker-agent-1 --tail 50"
echo "  3. Si ves '[pred] ... chosen=' es que funciona"
echo "  4. Espera 20 más segundos, a veces tarda en guardar"
echo ""

echo -e "${GREEN}✅ ¡Listo para verificar AP3!${NC}"
