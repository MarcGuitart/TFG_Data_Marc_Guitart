# 🤖 Adaptive Multi-Horizon Forecasting System with Intelligent Agent

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-18.0+-61DAFB.svg?logo=react)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Bachelor's Thesis Project** - Intelligent time series forecasting system with adaptive model selection based on memory and continuous learning.

---

## 📋 Table of Contents

- [Description](#-description)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Technologies Used](#-technologies-used)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [API Endpoints](#-api-endpoints)
- [Visualizations](#-visualizations)
- [Advanced Configuration](#-advanced-configuration)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)
- [Author](#-author)

---

## 🎯 Description

This project implements an **adaptive time series forecasting system** that combines multiple forecasting models (Linear Regression, Polynomial, Alpha-Beta, Kalman Filter) with an intelligent agent that dynamically selects the best model at each instant.

The system uses a **weight-based memory mechanism** that continuously learns from the historical performance of each model, enabling:

- 🔮 **Multi-horizon predictions**: From T+1 to T+200 (configurable)
- 🧠 **Adaptive selection**: The agent chooses the optimal model in real-time
- 📊 **Ranking system**: Models classified by cumulative performance
- 🎯 **Memory with decay**: Weights evolve based on recent performance
- 📈 **Real-time visualization**: Interactive dashboard with React
- 🔄 **Streaming pipeline**: Continuous processing with Kafka

### 🎓 Academic Context

This project is part of a Bachelor's Thesis in Computer Engineering, focused on:
- Multi-agent systems
- Machine Learning applied to time series
- Microservices architectures
- Streaming data processing
- Scientific data visualization

---

## ✨ Key Features

### 🤖 Intelligent Agent with Memory

- **Dynamic weight system**: Each model accumulates points based on its performance
- **Adaptive ranking**: Top-3 models with visual indicators (Trophy, Medal, Award icons)
- **Exponential decay memory**: Greater weight to recent predictions
- **History export**: Complete CSV with weight evolution

### 📊 Multi-Perspective Analysis (AP1-AP4)

1. **AP1 - Global Chart**: Complete visualization of predictions vs observations
   - Main chart with independent X/Y zoom
   - View by horizon (T+1, T+M)
   - Confidence intervals

2. **AP2 - Adaptive Selector**: Detailed table of agent decisions
   - Model chosen at each instant
   - Point-wise relative error
   - Real vs predicted values

3. **AP3 - Weight Evolution**: Temporal graphs of the memory system
   - Weight evolution by model
   - Cumulative statistics
   - Comparison chosen_by_error vs chosen_by_weight

4. **AP4 - Model Ranking**: Table with MAE, RMSE, MAPE metrics
   - Top-3 models highlighted
   - Cumulative final weight
   - Mean relative error

### 🎯 Multi-Horizon Prediction

- Flexible horizon configuration: 1 to 200 steps ahead
- Each step = 30 minutes of forecast
- Simultaneous visualization of multiple horizons
- Confidence intervals per horizon

### 📈 Advanced Metrics

- **MAE** (Mean Absolute Error)
- **RMSE** (Root Mean Square Error)
- **MAPE** (Mean Absolute Percentage Error)
- **Mean Relative Error** (%)
- **Confidence per horizon**: 1 - MAPE
- **Moving Average Accuracy**: Smoothing with moving window

### 🔄 Streaming Data Pipeline

- **Kafka**: Message queues for real-time data
- **InfluxDB**: Time series database
- **Window Loader**: Window-based data loading
- **Window Collector**: Collection of predictions and metrics

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│      Interactive Dashboard with Visualizations (Recharts)   │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST API
┌────────────────────▼────────────────────────────────────────┐
│                   ORCHESTRATOR (FastAPI)                     │
│  • Main endpoint management                                  │
│  • Metrics analysis                                          │
│  • Scenario management                                       │
│  • Services proxy                                            │
└─┬────────────────┬──────────────────┬───────────────────────┘
  │                │                  │
  ▼                ▼                  ▼
┌───────────┐  ┌──────────────┐  ┌────────────────┐
│  AGENT    │  │WINDOW_LOADER │  │WINDOW_COLLECTOR│
│ (Python)  │  │   (Python)   │  │    (Python)    │
│           │  │              │  │                │
│ • Models  │  │ • CSV Load   │  │ • Collect      │
│ • Weights │  │ • Kafka      │  │   predictions  │
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

### Data Flow

1. **Loading**: Window Loader reads CSV and publishes to Kafka
2. **Prediction**: Agent processes each point, generates multi-horizon predictions
3. **Collection**: Window Collector stores in InfluxDB
4. **Analysis**: Orchestrator queries metrics and exposes API
5. **Visualization**: Frontend consumes API and displays interactive dashboards

---

## 🛠️ Technologies Used

### Backend

- **Python 3.9+**: Primary language
- **FastAPI**: Asynchronous web framework
- **Pandas / NumPy**: Data processing
- **Scikit-learn**: ML models
- **Kafka-Python**: Apache Kafka client
- **InfluxDB-Client**: InfluxDB client
- **Pydantic**: Data validation

### Frontend

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Recharts**: Charts and visualizations
- **Lucide React**: SVG icons
- **Axios**: HTTP client

### Infrastructure

- **Docker & Docker Compose**: Container orchestration
- **Apache Kafka**: Data streaming
- **InfluxDB 2.x**: Time series database
- **Nginx** (optional): Reverse proxy

---

## 📦 Prerequisites

### Required Software

- **Docker Desktop** 4.0+ ([Download](https://www.docker.com/products/docker-desktop))
- **Docker Compose** 2.0+
- **Git** ([Download](https://git-scm.com/))

### Recommended Hardware

- **RAM**: 8 GB minimum (16 GB recommended)
- **Disk**: 10 GB free space
- **CPU**: 4 cores (for optimal execution)

### Optional (for local development without Docker)

- **Node.js** 18+ & npm 9+
- **Python** 3.9+ & pip
- **Make** (for simplified commands)

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/MarcGuitart/TFG_Data_Marc_Guitart.git
cd TFG_Data_Marc_Guitart
```

### 2. Configure Environment Variables

```bash
# Copy example file
cp config/app.env.example config/app.env

# Edit if necessary (default values work with Docker)
nano config/app.env
```

### 3. Start the System with Docker

```bash
# Build images and start services
docker-compose -f docker/docker-compose.yml up --build

# Or in detached mode (background)
docker-compose -f docker/docker-compose.yml up -d --build
```

### 4. Verify Services are Running

```bash
# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Check containers
docker ps
```

You should see these services running:
- `agent` (port 8090)
- `orchestrator` (port 8081)
- `window_loader` (port 8083)
- `window_collector` (port 8082)
- `kafka` (port 9092)
- `influxdb` (port 8086)
- `frontend` (port 5173)

### 5. Access the Application

Open your browser at:

```
http://localhost:5173
```

---

## 🎮 Usage

### Basic Workflow

#### 1. Load Data

From the web UI:

1. Go to the **"Upload CSV"** section
2. Select a CSV file with format:
   ```csv
   timestamp,value,unit_id
   2025-01-01 00:00:00,0.123,unit_01
   2025-01-01 00:30:00,0.145,unit_01
   ...
   ```
3. Click **"Upload"**

Or use the included example data:

```bash
# Example data is in /data/ (ignored by git)
# You can load: demo_final.csv, test_complete.csv, etc.
```

#### 2. Configure Prediction Horizon

In the control panel:

- **Horizon Selector**: Choose from 1 to 200 steps
- **Speed**: Processing speed (0 = maximum speed)
- **Source**: CSV file to process

#### 3. Run Prediction

```bash
# From UI: "Run Window" button

# Or via API:
curl -X POST "http://localhost:8081/api/run_window?source=demo_final.csv&speed_ms=0&forecast_horizon=20"
```

#### 4. Explore Results

- **Demo Tab**: Quick view with predictions and metrics
- **Complete Analysis**: Detailed analysis with all horizons
- **Confidence Evolution**: Temporal evolution of confidence
- **AP2 Selector**: Agent decision table
- **AP3 Weights**: Weight evolution by model
- **AP4 Ranking**: Top-3 table with global metrics

#### 5. Export Results

```bash
# Export weight history
curl -X POST "http://localhost:8081/api/agent/export_csv/unit_01"

# Download CSV
curl "http://localhost:8081/api/download_weights/unit_01" -o weights_history.csv
```

### Useful Make Commands

```bash
# View help
make help

# Start services
make up

# View logs
make logs

# Stop services
make down

# Clean everything (including volumes)
make clean

# Rebuild from scratch
make rebuild
```

---

## 📁 Project Structure

```
TFG_Agente_Data/
├── 📄 README.md                    # This file
├── 📄 docker-compose.yml           # Service orchestration
├── 📄 Makefile                     # Simplified commands
├── 📄 .gitignore                   # Files ignored by Git
│
├── 📁 services/                    # Backend microservices
│   ├── 📁 agent/                   # Intelligent agent with models
│   │   ├── app.py                  # FastAPI app
│   │   ├── models.py               # Model implementations
│   │   ├── memory_system.py       # Weight and ranking system
│   │   └── Dockerfile
│   │
│   ├── 📁 orchestrator/            # Main service (API)
│   │   ├── app.py                  # Main endpoints
│   │   ├── scenarios.py            # Scenario management
│   │   └── Dockerfile
│   │
│   ├── 📁 window_loader/           # Kafka data loading
│   │   ├── app.py
│   │   └── Dockerfile
│   │
│   ├── 📁 window_collector/        # InfluxDB collection
│   │   ├── app.py
│   │   └── Dockerfile
│   │
│   └── 📁 common/                  # Shared utilities
│       └── utils.py
│
├── 📁 frontend/                    # React application
│   ├── 📁 src/
│   │   ├── 📁 components/          # React components
│   │   │   ├── AP1GlobalChart.jsx  # Global chart
│   │   │   ├── AP2SelectorTable.jsx # Selector table
│   │   │   ├── AP3WeightsPanel.jsx # Weights panel
│   │   │   ├── AP4MetricsTable.jsx # Model ranking
│   │   │   ├── PredictionPanel.jsx # Main panel
│   │   │   └── ...
│   │   ├── App.jsx                 # Root component
│   │   └── main.jsx                # Entry point
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── 📁 config/                      # Configurations
│   ├── app.env.example             # Environment variables (example)
│   ├── schema.json                 # Validation schema
│   └── topics.yaml                 # Kafka topics configuration
│
├── 📁 data/                        # Data (ignored by git)
│   ├── .gitkeep
│   └── (example CSV files)
│
├── 📁 docs/                        # Additional documentation
│   └── (development documents)
│
├── 📁 scripts/                     # Utility scripts
│   └── plot_csv.py                 # CSV visualization
│
├── 📁 utils/                       # Python utilities
│   ├── analyze_ap3_weights.py
│   └── example_export_structure.py
│
└── 📁 docker/                      # Dockerfiles and configs
    ├── docker-compose.yml
    ├── Dockerfile.agent
    ├── Dockerfile.orchestrator
    ├── Dockerfile.window_collector
    └── Dockerfile.window_loader
```

---

## 🌐 API Endpoints

### Orchestrator (port 8081)

#### Data and Predictions

```http
GET  /api/series?id={id}&hours={hours}
GET  /api/forecast_multi_horizon?id={id}&hours={hours}
GET  /api/forecast_horizon
GET  /api/ids
POST /api/run_window?source={file}&speed_ms={ms}&forecast_horizon={n}
POST /api/reset_system
POST /api/upload_csv
```

#### Metrics and Analysis

```http
GET /api/metrics/combined?id={id}&start={start}
GET /api/metrics/models?id={id}&start={start}
GET /api/metrics/models/ranked?id={id}&start={start}
GET /api/selector?id={id}&hours={hours}
```

#### Agent and Weights (AP3)

```http
GET  /api/agent/weights/{unit_id}
GET  /api/agent/history/{unit_id}?last_n={n}
GET  /api/agent/stats/{unit_id}
POST /api/agent/export_csv/{unit_id}
GET  /api/download_weights/{unit_id}
```

#### Scenarios

```http
POST   /api/scenarios/save?scenario_name={name}&unit_id={id}
GET    /api/scenarios/list
GET    /api/scenarios/load/{scenario_name}
POST   /api/scenarios/compare
DELETE /api/scenarios/delete/{scenario_name}
```

#### Advanced Analysis (AI)

```http
POST /api/analyze_report/{id}
POST /api/analyze_report_advanced/{id}
```

### Agent (port 8090)

```http
POST /predict              # Multi-horizon prediction
GET  /weights/{unit_id}    # Get current weights
GET  /history/{unit_id}    # Weight history
GET  /stats/{unit_id}      # Statistics per model
POST /export_csv/{unit_id} # Export complete history
POST /reset/{unit_id}      # Reset memory
```

### Interactive Documentation

- Orchestrator: [http://localhost:8081/docs](http://localhost:8081/docs)
- Agent: [http://localhost:8090/docs](http://localhost:8090/docs)

---

## 📊 Visualizations

### AP1 - Global Chart
![AP1 Global Chart](docs/images/ap1_global_chart.png)
- Complete chart of observations vs predictions
- Independent X/Y zoom
- Visualization by horizon (T+1, T+20, etc.)
- Confidence intervals

### AP2 - Adaptive Selector
![AP2 Selector](docs/images/ap2_selector.png)
- Table with step-by-step decisions
- Model chosen at each instant
- Point-wise relative error
- Real vs predicted values

### AP3 - Weight Evolution
![AP3 Weights](docs/images/ap3_weights.png)
- Temporal chart of weights per model
- Cumulative statistics table
- Comparison chosen_by_error vs chosen_by_weight
- History export

### AP4 - Model Ranking
![AP4 Ranking](docs/images/ap4_ranking.png)
- Top-3 models with badges (🏆🥈🥉)
- MAE, RMSE, MAPE metrics
- Final cumulative weight
- Mean relative error

---

## ⚙️ Advanced Configuration

### Environment Variables

File: `config/app.env`

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

# Processing
DATA_PATH=/app/data/demo_final.csv
PROCESS_MODE=scale_v1
DEDUP_KEY=ts,unit_id

# Agent
MEMORY_DECAY=0.95
MEMORY_SIZE=100
MIN_WEIGHT=-10.0
MAX_WEIGHT=10.0

# Groq API (optional, for AI analysis)
GROQ_API_KEY=your_api_key_here
```

### Docker Compose Configuration

File: `docker/docker-compose.yml`

You can adjust:
- Resources (CPU, memory)
- Exposed ports
- Persistent volumes
- Environment variables

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

### Customize Models

Edit `services/agent/models.py` to:
- Add new forecasting models
- Modify existing hyperparameters
- Change ensemble strategy

### Adjust Memory System

Edit `services/agent/memory_system.py`:
- `DECAY_FACTOR`: Exponential decay factor (0-1)
- `MEMORY_SIZE`: Memory window size
- `MIN_WEIGHT` / `MAX_WEIGHT`: Weight limits

---

## 🧪 Testing

### Unit Tests

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

### Integration Tests

```bash
# Start complete system
docker-compose -f docker/docker-compose.yml up -d

# Run test suite
python tests/integration/test_full_pipeline.py
```

### Manual Verification

```bash
# Check health endpoints
curl http://localhost:8081/health
curl http://localhost:8090/health

# Test simple prediction
curl -X POST http://localhost:8090/predict \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2025-01-01T00:00:00", "value": 0.123, "unit_id": "test"}'
```

---

## 🤝 Contributing

This project is an academic Bachelor's Thesis, but contributions are welcome for future improvements:

1. **Fork** the repository
2. Create a **branch** for your feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** your changes (`git commit -m 'Add some AmazingFeature'`)
4. **Push** to the branch (`git push origin feature/AmazingFeature`)
5. Open a **Pull Request**

### Guidelines

- Python code: follow [PEP 8](https://pep8.org/)
- JavaScript code: follow [Airbnb Style Guide](https://github.com/airbnb/javascript)
- Commits: descriptive messages in English
- Tests: include tests for new features

---

## 📄 License

This project is licensed under the **MIT License**.

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

## 🙏 Acknowledgments

- **Thesis Director**: [Thesis Director Name]
- **University**: Universitat Politècnica de Catalunya (UPC)
- **Faculty**: Facultat d'Informàtica de Barcelona (FIB)
- **Academic Year**: 2025-2026

### Open Source Technologies Used

- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework for Python
- [React](https://reactjs.org/) - UI library for interactive interfaces
- [Recharts](https://recharts.org/) - Charting library for React
- [Apache Kafka](https://kafka.apache.org/) - Distributed streaming platform
- [InfluxDB](https://www.influxdata.com/) - Time series database
- [Docker](https://www.docker.com/) - Container platform

---

## 📚 References and Resources

### Papers and Articles

1. **Time Series Forecasting**: [Forecasting: Principles and Practice](https://otexts.com/fpp3/)
2. **Ensemble Learning**: "Ensemble methods in machine learning" - Dietterich (2000)
3. **Adaptive Systems**: "Adaptive Learning Systems" - IEEE Transactions

### Technical Documentation

- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [InfluxDB Docs](https://docs.influxdata.com/)
- [FastAPI Guide](https://fastapi.tiangolo.com/tutorial/)
- [React Docs](https://react.dev/)

### Datasets and Benchmarks

- [M4 Competition](https://www.m4.unic.ac.cy/)
- [Time Series Data Library](https://datamarket.com/data/list/?q=provider:tsdl)

---

## 🔮 Future Roadmap

### Upcoming Features

- [ ] Support for more models (LSTM, Prophet, ARIMA)
- [ ] Probabilistic prediction with Bayesian confidence intervals
- [ ] Dashboard with real-time metrics (WebSockets)
- [ ] GraphQL API for more flexible queries
- [ ] Multi-tenancy support
- [ ] Automatic clustering of similar series
- [ ] Hyperparameter auto-tuning with Optuna
- [ ] Export to Parquet, Avro formats
- [ ] MLflow integration for experiment tracking

### Technical Improvements

- [ ] End-to-end tests with Playwright
- [ ] CI/CD with GitHub Actions
- [ ] Kubernetes deployment
- [ ] Monitoring with Prometheus + Grafana
- [ ] Automatic documentation with Sphinx

---

## ❓ FAQ

### How do I change the prediction horizon?

From the UI, adjust the "Forecast Horizon" selector or via API:

```bash
curl -X POST "http://localhost:8081/api/run_window?forecast_horizon=50"
```

### Can I use my own data?

Yes, you just need a CSV with columns: `timestamp`, `value`, `unit_id`

### How do I reset the system?

```bash
curl -X POST http://localhost:8081/api/reset_system
```

Or from the UI: "Reset System" button

### What if the services don't start?

```bash
# View logs to diagnose
docker-compose -f docker/docker-compose.yml logs

# Rebuild from scratch
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up --build
```

### How do I export results?

Use the export endpoints:

```bash
# Weights history
curl http://localhost:8081/api/download_weights/unit_01 -o weights.csv

# Metrics
curl "http://localhost:8081/api/metrics/models/ranked?id=unit_01" | jq . > metrics.json
```

---

## 📞 Support

If you encounter any issues or have questions:

1. Review the [FAQ section](#-faq)
2. Search in [Issues](https://github.com/MarcGuitart/TFG_Data_Marc_Guitart/issues)
3. Open a new Issue with details (logs, screenshots, etc.)
4. Contact the author via email

---

<div align="center">

**⭐ If this project has been useful to you, consider giving it a star on GitHub ⭐**

[🔝 Back to top](#-adaptive-multi-horizon-forecasting-system-with-intelligent-agent)

</div>
