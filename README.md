# 🤖 Sistema Adaptativo de Predicción Multi-Horizonte con Agente Inteligente

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB.svg?logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Trabajo de Fin de Grado (TFG)** - Sistema inteligente de predicción de series temporales con selección adaptativa de modelos basada en memoria y aprendizaje continuo.

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Características Principales](#-características-principales)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Tecnologías Utilizadas](#-tecnologías-utilizadas)
- [Requisitos Previos](#-requisitos-previos)
- [Instalación](#-instalación)
- [Uso](#-uso)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [API Endpoints](#-api-endpoints)
- [Visualizaciones](#-visualizaciones)
- [Configuración Avanzada](#-configuración-avanzada)
- [Testing](#-testing)
- [Contribución](#-contribución)
- [Licencia](#-licencia)
- [Autor](#-autor)

---

## 🎯 Descripción

Este proyecto implementa un **sistema adaptativo de predicción de series temporales** que combina múltiples modelos de forecasting (Linear Regression, Polynomial, Alpha-Beta, Kalman Filter) con un agente inteligente que selecciona dinámicamente el mejor modelo en cada instante.

El sistema utiliza un **mecanismo de memoria con pesos** que aprende continuamente del rendimiento histórico de cada modelo, permitiendo:

- 🔮 **Predicciones multi-horizonte**: Desde T+1 hasta T+200 (configurable)
- 🧠 **Selección adaptativa**: El agente elige el modelo óptimo en tiempo real
- 📊 **Sistema de ranking**: Modelos clasificados por desempeño acumulado
- 🎯 **Memoria con decay**: Los pesos evolucionan según el rendimiento reciente
- 📈 **Visualización en tiempo real**: Dashboard interactivo con React
- 🔄 **Pipeline streaming**: Procesamiento continuo con Kafka

### 🎓 Contexto Académico

Este proyecto forma parte de un Trabajo de Fin de Grado en Ingeniería Informática, enfocado en:
- Sistemas multi-agente
- Machine Learning aplicado a series temporales
- Arquitecturas de microservicios
- Procesamiento de datos en streaming
- Visualización de datos científicos

---

## ✨ Características Principales

### 🤖 Agente Inteligente con Memoria

- **Sistema de pesos dinámico**: Cada modelo acumula puntos según su desempeño
- **Ranking adaptativo**: Top-3 modelos con indicadores visuales
- **Memoria con decay exponencial**: Mayor peso a predicciones recientes
- **Exportación de historial**: CSV completo con evolución de pesos

### 📊 Análisis Multi-Perspectiva (AP1-AP4)

1. **AP1 - Global Chart**: Visualización completa de predicciones vs observaciones
2. **AP2 - Selector Adaptativo**: Tabla detallada de decisiones del agente
3. **AP3 - Evolución de Pesos**: Gráficos temporales del sistema de memoria
4. **AP4 - Ranking de Modelos**: Tabla con métricas MAE, RMSE, MAPE

### 🎯 Predicción Multi-Horizonte

- Configuración flexible de horizonte: 1 a 200 pasos adelante
- Cada paso = 30 minutos de forecast
- Visualización simultánea de múltiples horizontes
- Intervalos de confianza por horizonte

### 📈 Métricas Avanzadas

- **MAE** (Mean Absolute Error)
- **RMSE** (Root Mean Square Error)
- **MAPE** (Mean Absolute Percentage Error)
- **Error Relativo Medio** (%)
- **Confianza por horizonte**: 1 - MAPE
- **Moving Average Accuracy**: Suavizado con ventana móvil

### 🔄 Pipeline de Datos en Streaming

- **Kafka**: Colas de mensajería para datos en tiempo real
- **InfluxDB**: Base de datos de series temporales
- **Window Loader**: Carga de datos por ventanas
- **Window Collector**: Recolección de predicciones y métricas

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│  Dashboard Interactivo con Visualizaciones (Recharts)       │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────────────┐
│                   ORCHESTRATOR (FastAPI)                     │
│  • Gestión de endpoints principales                          │
│  • Análisis de métricas                                      │
│  • Gestión de escenarios                                     │
│  • Proxy a servicios                                         │
└─┬────────────────┬──────────────────┬───────────────────────┘
  │                │                  │
  ▼                ▼                  ▼
┌───────────┐  ┌──────────────┐  ┌────────────────┐
│  AGENT    │  │WINDOW_LOADER │  │WINDOW_COLLECTOR│
│ (Python)  │  │   (Python)   │  │    (Python)    │
│           │  │              │  │                │
│ • Modelos │  │ • Carga CSV  │  │ • Recolecta    │
│ • Pesos   │  │ • Kafka      │  │   predicciones │
│ • Ranking │  │   Producer   │  │ • InfluxDB     │
└─────┬─────┘  └──────┬───────┘  └────────┬───────┘
      │               │                   │
      └───────────────┼───────────────────┘
                      ▼
              ┌──────────────┐
              │    KAFKA     │
              │  (Streaming) │
              └──────┬───────┘
                     │
              ┌──────▼───────┐
              │  INFLUXDB    │
              │ (TimeSeries) │
              └──────────────┘
```

### Flujo de Datos

1. **Carga**: Window Loader lee CSV y publica en Kafka
2. **Predicción**: Agent procesa cada punto, genera predicciones multi-horizonte
3. **Recolección**: Window Collector almacena en InfluxDB
4. **Análisis**: Orchestrator consulta métricas y expone API
5. **Visualización**: Frontend consume API y muestra dashboards interactivos

---

## 🛠️ Tecnologías Utilizadas

### Backend

- **Python 3.9+**: Lenguaje principal
- **FastAPI**: Framework web asíncrono
- **Pandas / NumPy**: Procesamiento de datos
- **Scikit-learn**: Modelos de ML
- **Kafka-Python**: Cliente de Apache Kafka
- **InfluxDB-Client**: Cliente de InfluxDB
- **Pydantic**: Validación de datos

### Frontend

- **React 18**: Framework UI
- **Vite**: Build tool y dev server
- **Recharts**: Gráficos y visualizaciones
- **Lucide React**: Iconos SVG
- **Axios**: Cliente HTTP

### Infraestructura

- **Docker & Docker Compose**: Orquestación de contenedores
- **Apache Kafka**: Streaming de datos
- **InfluxDB 2.x**: Base de datos de series temporales
- **Nginx** (opcional): Reverse proxy

---

## 📦 Requisitos Previos

### Software Necesario

- **Docker Desktop** 4.0+ ([Descargar](https://www.docker.com/products/docker-desktop))
- **Docker Compose** 2.0+
- **Git** ([Descargar](https://git-scm.com/))

### Hardware Recomendado

- **RAM**: 8 GB mínimo (16 GB recomendado)
- **Disco**: 10 GB libres
- **CPU**: 4 cores (para ejecución óptima)

### Opcional (para desarrollo local sin Docker)

- **Node.js** 18+ & npm 9+
- **Python** 3.9+ & pip
- **Make** (para comandos simplificados)

---

## 🚀 Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/MarcGuitart/TFG_Data_Marc_Guitart.git
cd TFG_Data_Marc_Guitart
```

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp config/app.env.example config/app.env

# Editar si es necesario (valores por defecto funcionan con Docker)
nano config/app.env
```

### 3. Levantar el Sistema con Docker

```bash
# Construir imágenes y levantar servicios
docker-compose -f docker/docker-compose.yml up --build

# O en segundo plano (detached)
docker-compose -f docker/docker-compose.yml up -d --build
```

### 4. Verificar que los Servicios están Activos

```bash
# Ver logs
docker-compose -f docker/docker-compose.yml logs -f

# Verificar contenedores
docker ps
```

Deberías ver estos servicios corriendo:
- `agent` (puerto 8090)
- `orchestrator` (puerto 8081)
- `window_loader` (puerto 8083)
- `window_collector` (puerto 8082)
- `kafka` (puerto 9092)
- `influxdb` (puerto 8086)
- `frontend` (puerto 5173)

### 5. Acceder a la Aplicación

Abre tu navegador en:

```
http://localhost:5173
```

---

## 🎮 Uso

### Flujo Básico de Trabajo

#### 1. Cargar Datos

Desde la UI web:

1. Ve a la sección **"Upload CSV"**
2. Selecciona un archivo CSV con formato:
   ```csv
   timestamp,value,unit_id
   2025-01-01 00:00:00,0.123,unit_01
   2025-01-01 00:30:00,0.145,unit_01
   ...
   ```
3. Haz clic en **"Upload"**

O usa los datos de ejemplo incluidos:

```bash
# Los datos de ejemplo están en /data/ (ignorados por git)
# Puedes cargar: demo_final.csv, test_complete.csv, etc.
```

#### 2. Configurar Horizonte de Predicción

En el panel de control:

- **Selector de Horizonte**: Elige de 1 a 200 pasos
- **Speed**: Velocidad de procesamiento (0 = máxima velocidad)
- **Source**: Archivo CSV a procesar

#### 3. Ejecutar Predicción

```bash
# Desde la UI: botón "Run Window"

# O vía API:
curl -X POST "http://localhost:8081/api/run_window?source=demo_final.csv&speed_ms=0&forecast_horizon=20"
```

#### 4. Explorar Resultados

- **Demo Tab**: Vista rápida con predicciones y métricas
- **Complete Analysis**: Análisis detallado con todos los horizontes
- **Confidence Evolution**: Evolución temporal de la confianza
- **AP2 Selector**: Tabla de decisiones del agente
- **AP3 Weights**: Evolución de pesos por modelo
- **AP4 Ranking**: Tabla Top-3 con métricas globales

#### 5. Exportar Resultados

```bash
# Exportar historial de pesos
curl -X POST "http://localhost:8081/api/agent/export_csv/unit_01"

# Descargar CSV
curl "http://localhost:8081/api/download_weights/unit_01" -o weights_history.csv
```

### Comandos Útiles con Make

```bash
# Ver ayuda
make help

# Levantar servicios
make up

# Ver logs
make logs

# Parar servicios
make down

# Limpiar todo (volúmenes incluidos)
make clean

# Reconstruir desde cero
make rebuild
```

---

## 📁 Estructura del Proyecto

```
TFG_Agente_Data/
├── 📄 README.md                    # Este archivo
├── 📄 docker-compose.yml           # Orquestación de servicios
├── 📄 Makefile                     # Comandos simplificados
├── 📄 .gitignore                   # Archivos ignorados por Git
│
├── 📁 services/                    # Microservicios backend
│   ├── 📁 agent/                   # Agente inteligente con modelos
│   │   ├── app.py                  # FastAPI app
│   │   ├── models.py               # Implementación de modelos
│   │   ├── memory_system.py       # Sistema de pesos y ranking
│   │   └── Dockerfile
│   │
│   ├── 📁 orchestrator/            # Servicio principal (API)
│   │   ├── app.py                  # Endpoints principales
│   │   ├── scenarios.py            # Gestión de escenarios
│   │   └── Dockerfile
│   │
│   ├── 📁 window_loader/           # Carga de datos en Kafka
│   │   ├── app.py
│   │   └── Dockerfile
│   │
│   ├── 📁 window_collector/        # Recolección en InfluxDB
│   │   ├── app.py
│   │   └── Dockerfile
│   │
│   └── 📁 common/                  # Utilidades compartidas
│       └── utils.py
│
├── 📁 frontend/                    # Aplicación React
│   ├── 📁 src/
│   │   ├── 📁 components/          # Componentes React
│   │   │   ├── AP1GlobalChart.jsx  # Gráfico global
│   │   │   ├── AP2SelectorTable.jsx # Tabla selector
│   │   │   ├── AP3WeightsPanel.jsx # Panel de pesos
│   │   │   ├── AP4MetricsTable.jsx # Ranking de modelos
│   │   │   ├── PredictionPanel.jsx # Panel principal
│   │   │   └── ...
│   │   ├── App.jsx                 # Componente raíz
│   │   └── main.jsx                # Punto de entrada
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── 📁 config/                      # Configuraciones
│   ├── app.env.example             # Variables de entorno (ejemplo)
│   ├── schema.json                 # Schema de validación
│   └── topics.yaml                 # Configuración de topics Kafka
│
├── 📁 data/                        # Datos (ignorado por git)
│   ├── .gitkeep
│   └── (archivos CSV de ejemplo)
│
├── 📁 docs/                        # Documentación adicional
│   └── (documentos de desarrollo)
│
├── 📁 scripts/                     # Scripts de utilidad
│   └── plot_csv.py                 # Visualización de CSVs
│
├── 📁 utils/                       # Utilidades Python
│   ├── analyze_ap3_weights.py
│   └── example_export_structure.py
│
└── 📁 docker/                      # Dockerfiles y configs
    ├── docker-compose.yml
    ├── Dockerfile.agent
    ├── Dockerfile.orchestrator
    ├── Dockerfile.window_collector
    └── Dockerfile.window_loader
```

---

## 🌐 API Endpoints

### Orchestrator (puerto 8081)

#### Datos y Predicciones

```http
GET  /api/series?id={id}&hours={hours}
GET  /api/forecast_multi_horizon?id={id}&hours={hours}
GET  /api/forecast_horizon
GET  /api/ids
POST /api/run_window?source={file}&speed_ms={ms}&forecast_horizon={n}
POST /api/reset_system
POST /api/upload_csv
```

#### Métricas y Análisis

```http
GET /api/metrics/combined?id={id}&start={start}
GET /api/metrics/models?id={id}&start={start}
GET /api/metrics/models/ranked?id={id}&start={start}
GET /api/selector?id={id}&hours={hours}
```

#### Agente y Pesos (AP3)

```http
GET  /api/agent/weights/{unit_id}
GET  /api/agent/history/{unit_id}?last_n={n}
GET  /api/agent/stats/{unit_id}
POST /api/agent/export_csv/{unit_id}
GET  /api/download_weights/{unit_id}
```

#### Escenarios

```http
POST   /api/scenarios/save?scenario_name={name}&unit_id={id}
GET    /api/scenarios/list
GET    /api/scenarios/load/{scenario_name}
POST   /api/scenarios/compare
DELETE /api/scenarios/delete/{scenario_name}
```

#### Análisis Avanzado (IA)

```http
POST /api/analyze_report/{id}
POST /api/analyze_report_advanced/{id}
```

### Agent (puerto 8090)

```http
POST /predict              # Predicción multi-horizonte
GET  /weights/{unit_id}    # Obtener pesos actuales
GET  /history/{unit_id}    # Historial de pesos
GET  /stats/{unit_id}      # Estadísticas por modelo
POST /export_csv/{unit_id} # Exportar historial completo
POST /reset/{unit_id}      # Resetear memoria
```

### Documentación Interactiva

- Orchestrator: [http://localhost:8081/docs](http://localhost:8081/docs)
- Agent: [http://localhost:8090/docs](http://localhost:8090/docs)

---

## 📊 Visualizaciones

### AP1 - Global Chart
![AP1 Global Chart](docs/images/ap1_global_chart.png)
- Gráfico completo de observaciones vs predicciones
- Zoom X/Y independiente
- Visualización por horizonte (T+1, T+20, etc.)
- Intervalos de confianza

### AP2 - Selector Adaptativo
![AP2 Selector](docs/images/ap2_selector.png)
- Tabla con decisiones paso a paso
- Modelo elegido en cada instante
- Error relativo puntual
- Valores real vs predicho

### AP3 - Evolución de Pesos
![AP3 Weights](docs/images/ap3_weights.png)
- Gráfico temporal de pesos por modelo
- Tabla de estadísticas acumuladas
- Comparación chosen_by_error vs chosen_by_weight
- Exportación de historial

### AP4 - Ranking de Modelos
![AP4 Ranking](docs/images/ap4_ranking.png)
- Top-3 modelos con badges (🏆🥈🥉)
- Métricas MAE, RMSE, MAPE
- Weight final acumulado
- Error relativo medio

---

## ⚙️ Configuración Avanzada

### Variables de Entorno

Archivo: `config/app.env`

```bash
# Kafka
KAFKA_BROKER=kafka:9092
TOPIC_AGENT_IN=telemetry.agent.in
TOPIC_AGENT_OUT=telemetry.agent.out

# InfluxDB
INFLUX_URL=http://influxdb:8086
INFLUX_TOKEN=admin_token
INFLUX_ORG=tfg
INFLUX_BUCKET=pipeline

# Procesamiento
DATA_PATH=/app/data/demo_final.csv
PROCESS_MODE=scale_v1
DEDUP_KEY=ts,unit_id

# Agent
MEMORY_DECAY=0.95
MEMORY_SIZE=100
MIN_WEIGHT=-10.0
MAX_WEIGHT=10.0

# Groq API (opcional, para análisis IA)
GROQ_API_KEY=your_api_key_here
```

### Configuración de Docker Compose

Archivo: `docker/docker-compose.yml`

Puedes ajustar:
- Recursos (CPU, memoria)
- Puertos expuestos
- Volúmenes persistentes
- Variables de entorno

```yaml
services:
  agent:
    build: ./services/agent
    environment:
      - MEMORY_DECAY=0.95
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
```

### Personalizar Modelos

Edita `services/agent/models.py` para:
- Añadir nuevos modelos de forecasting
- Modificar hiperparámetros existentes
- Cambiar estrategia de ensemble

### Ajustar Sistema de Memoria

Edita `services/agent/memory_system.py`:
- `DECAY_FACTOR`: Factor de decay exponencial (0-1)
- `MEMORY_SIZE`: Tamaño de ventana de memoria
- `MIN_WEIGHT` / `MAX_WEIGHT`: Límites de pesos

---

## 🧪 Testing

### Tests Unitarios

```bash
# Backend (Python)
cd services/agent
pytest tests/

cd services/orchestrator
pytest tests/

# Frontend (JavaScript)
cd frontend
npm run test
```

### Tests de Integración

```bash
# Levantar sistema completo
docker-compose -f docker/docker-compose.yml up -d

# Ejecutar suite de tests
python tests/integration/test_full_pipeline.py
```

### Verificación Manual

```bash
# Check health endpoints
curl http://localhost:8081/health
curl http://localhost:8090/health

# Test predicción simple
curl -X POST http://localhost:8090/predict \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2025-01-01T00:00:00", "value": 0.123, "unit_id": "test"}'
```

---

## 🤝 Contribución

Este proyecto es un TFG académico, pero las contribuciones son bienvenidas para mejoras futuras:

1. **Fork** el repositorio
2. Crea una **branch** para tu feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. **Push** a la branch (`git push origin feature/AmazingFeature`)
5. Abre un **Pull Request**

### Guidelines

- Código Python: seguir [PEP 8](https://pep8.org/)
- Código JavaScript: seguir [Airbnb Style Guide](https://github.com/airbnb/javascript)
- Commits: mensajes descriptivos en inglés
- Tests: incluir tests para nuevas features

---

## 📄 Licencia

Este proyecto está bajo la licencia **MIT License**.

```
MIT License

Copyright (c) 2026 Marc Guitart

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👤 Autor

**Marc Guitart**

- GitHub: [@MarcGuitart](https://github.com/MarcGuitart)
- LinkedIn: [Marc Guitart](https://www.linkedin.com/in/marcguitart)
- Email: marc.guitart@estudiant.upc.edu

---

## 🙏 Agradecimientos

- **Director del TFG**: [Nombre del director]
- **Universidad**: Universitat Politècnica de Catalunya (UPC)
- **Facultad**: Facultat d'Informàtica de Barcelona (FIB)
- **Curso**: 2025-2026

### Tecnologías Open Source Utilizadas

- [FastAPI](https://fastapi.tiangolo.com/) - Framework web moderno para Python
- [React](https://reactjs.org/) - Librería UI para interfaces interactivas
- [Recharts](https://recharts.org/) - Librería de gráficos para React
- [Apache Kafka](https://kafka.apache.org/) - Plataforma de streaming distribuido
- [InfluxDB](https://www.influxdata.com/) - Base de datos de series temporales
- [Docker](https://www.docker.com/) - Plataforma de contenedores

---

## 📚 Referencias y Recursos

### Papers y Artículos

1. **Time Series Forecasting**: [Forecasting: Principles and Practice](https://otexts.com/fpp3/)
2. **Ensemble Learning**: "Ensemble methods in machine learning" - Dietterich (2000)
3. **Adaptive Systems**: "Adaptive Learning Systems" - IEEE Transactions

### Documentación Técnica

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [InfluxDB Docs](https://docs.influxdata.com/)
- [FastAPI Guide](https://fastapi.tiangolo.com/tutorial/)
- [React Docs](https://react.dev/)

### Datasets y Benchmarks

- [M4 Competition](https://www.m4.unic.ac.cy/)
- [Time Series Data Library](https://datamarket.com/data/list/?q=provider:tsdl)

---

## 🔮 Roadmap Futuro

### Próximas Features

- [ ] Soporte para más modelos (LSTM, Prophet, ARIMA)
- [ ] Predicción probabilística con intervalos de confianza bayesianos
- [ ] Dashboard con métricas en tiempo real (WebSockets)
- [ ] API GraphQL para queries más flexibles
- [ ] Soporte multi-tenancy
- [ ] Clustering automático de series similares
- [ ] Auto-tuning de hiperparámetros con Optuna
- [ ] Exportación a formatos Parquet, Avro
- [ ] Integración con MLflow para tracking de experimentos

### Mejoras Técnicas

- [ ] Tests end-to-end con Playwright
- [ ] CI/CD con GitHub Actions
- [ ] Deployment en Kubernetes
- [ ] Monitoring con Prometheus + Grafana
- [ ] Documentación automática con Sphinx

---

## ❓ FAQ

### ¿Cómo cambio el horizonte de predicción?

Desde la UI, ajusta el selector "Forecast Horizon" o vía API:

```bash
curl -X POST "http://localhost:8081/api/run_window?forecast_horizon=50"
```

### ¿Puedo usar mis propios datos?

Sí, solo necesitas un CSV con columnas: `timestamp`, `value`, `unit_id`

### ¿Cómo reseteo el sistema?

```bash
curl -X POST http://localhost:8081/api/reset_system
```

O desde la UI: botón "Reset System"

### ¿Qué hacer si los servicios no levantan?

```bash
# Ver logs para diagnosticar
docker-compose -f docker/docker-compose.yml logs

# Reconstruir desde cero
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up --build
```

### ¿Cómo exporto resultados?

Usa los endpoints de exportación:

```bash
# Weights history
curl http://localhost:8081/api/download_weights/unit_01 -o weights.csv

# Métricas
curl "http://localhost:8081/api/metrics/models/ranked?id=unit_01" | jq . > metrics.json
```

---

## 📞 Soporte

Si encuentras algún problema o tienes preguntas:

1. Revisa la [sección FAQ](#-faq)
2. Busca en [Issues](https://github.com/MarcGuitart/TFG_Data_Marc_Guitart/issues)
3. Abre un nuevo Issue con detalles (logs, screenshots, etc.)
4. Contacta al autor via email

---

<div align="center">

**⭐ Si este proyecto te ha sido útil, considera darle una estrella en GitHub ⭐**

[🔝 Volver arriba](#-sistema-adaptativo-de-predicción-multi-horizonte-con-agente-inteligente)

</div>
