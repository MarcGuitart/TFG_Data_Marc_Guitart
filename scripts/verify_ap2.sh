#!/bin/bash

echo "🔍 Verificando logs del agente con modo adaptativo..."
echo "=================================================="
echo ""

echo "📝 Buscando predicciones con modelo elegido (chosen=):"
docker logs docker-agent-1 2>&1 | grep "chosen=" | tail -20

echo ""
echo "=================================================="
echo ""
echo "✅ Si ves líneas con 'chosen=linear_8' o 'chosen=poly2_12' o 'chosen=ab_fast', ¡AP2 FUNCIONA!"
echo ""
echo "🎯 Ahora verifica el frontend en http://localhost:5173"
echo "   - Deberías ver la tabla 'Selector Adaptativo'"
echo "   - Con timestamps y modelos elegidos en cada instante"
