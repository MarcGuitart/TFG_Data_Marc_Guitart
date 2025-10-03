# TFG Data Pipeline – Week 2

## 📌 Objetivo
Este proyecto implementa un **pipeline de ingesta y procesado de datos** basado en Kafka + InfluxDB.  
La **Week 2** se ha centrado en:
- Soporte de entrada desde **CSV y Parquet**
- Flujo **end-to-end** con Loader → Agent → Influx → Collector → Orchestrator
- Exposición de **métricas básicas** del sistema
- Implementación de **auto-gestión de la base de datos** en Influx
- Documentación y pruebas completas

---

## 🏗️ Arquitectura

```mermaid
flowchart LR
    subgraph Loader
        A[CSV / Parquet] --> B[window_loader]
    end

    B -->|telemetry.agent.in| C[agent]
    C -->|InfluxDB write| D[(InfluxDB)]
    C -->|telemetry.agent.out| E[window_collector]
    E -->|Flush + dedupe| F[/processed_window.csv/]
    E -->|API| G[orchestrator]

    G -->|/metrics, /flush| User[Cliente/API externa]
window_loader: lee archivos de entrada (CSV o Parquet), añade metadatos, publica en Kafka.
agent: recibe eventos → escribe en InfluxDB → reenvía mensajes procesados.
influxdb: almacenamiento de series temporales.
window_collector: deduplica por clave (timestamp,id) y expone un flush a disco.
orchestrator: API centralizada para cargar datos, ejecutar ventanas, consultar métricas y estado.
⚙️ Servicios (docker-compose)
Zookeeper – Coordina Kafka.
Kafka – Bus de mensajería entre servicios.
InfluxDB 2.7 – Base de datos de series temporales.
window_loader – Ingesta de ficheros → Kafka.
agent – Consumidor principal: transforma y escribe en Influx.
window_collector – Deduplicación + exportación de última ventana.
orchestrator – API REST para interacción externa.
🚀 Despliegue
# Build & levantar todos los servicios
docker compose build
docker compose up -d

# Ver logs de un servicio
docker compose logs -f agent
🧪 Flujo end-to-end
1. Subir un CSV de prueba
curl -X POST http://localhost:8081/api/upload_csv \
  -F "file=@data/test_csvs/test_small.csv"
Respuesta:
{"saved": true, "path": "/app/data/uploaded.csv"}
2. Ejecutar la ventana
curl -s -X POST http://localhost:8081/api/run_window | jq
Ejemplo de respuesta:
{
  "triggered": true,
  "status_code": 200,
  "loader_response": {
    "rows": 5,
    "path": "/app/data/processed_window.csv"
  }
}
3. Consultar collector (última versión)
curl -s http://localhost:8082/flush | jq
Ejemplo:
{
  "rows": 5,
  "path": "/app/data/processed_window.csv"
}
Y contenido del archivo:
timestamp,id,var,__src_format,ts
2024-01-01 00:00:01,unit-test,0.1,csv,2024-01-01 00:00:01
...
4. Validar en InfluxDB
docker compose exec influxdb influx query '
  from(bucket:"pipeline")
    |> range(start: -1h)
    |> filter(fn: (r) => r["_measurement"] == "telemetry")
    |> pivot(rowKey:["_time"], columnKey:["_field"], valueColumn:"_value")
    |> limit(n:10)
'
Ejemplo de salida:
_table | _time                          | unit      | var
------------------------------------------------------------
      0 | 2025-10-02T10:04:21.000000000Z | unit-test | 0.5
📊 Métricas expuestas
El orchestrator expone métricas internas:
curl -s http://localhost:8081/metrics | jq
Ejemplo:
{
  "uptime_sec": 120,
  "points_written": 0,
  "last_flush_rows": 5
}
Y en formato Prometheus:
curl -s http://localhost:8081/metrics/prometheus
uptime_sec 120
points_written 0
last_flush_rows 5
🧹 Auto-gestión de la DB
Cada 5 minutos, el agent ejecuta una limpieza automática (enforce_cap_per_unit()):
Cada unit tiene un límite máximo (MAX_ROWS_PER_UNIT, por defecto 1000 filas).
Si se excede, se eliminan datos más antiguos de 7 días.
Esto asegura que la base de datos no crezca indefinidamente.
✅ Checklist Week 2
 Loader soporta CSV + Parquet
 Agent escribe en InfluxDB con timestamps corregidos
 Collector guarda última versión y expone flush
 Orchestrator centraliza APIs (/upload_csv, /run_window, /flush, /metrics)
 Métricas básicas expuestas
 Auto-gestión de la DB implementada
 Documentación end-to-end