# NER Landslide Risk Monitoring System

An AI-based early warning and landslide risk monitoring platform customized for the **North Eastern Region (NER)** of India. This system uses satellite imagery, rainfall/weather telemetry, terrain slope profiles, historical landslides, and machine learning to estimate hazard levels and deliver early warning alerts.

---

## 1. Problem Being Solved
The North Eastern Region (NER) of India is highly susceptible to landslides due to heavy rainfall, steep terrain, seismicity, and geological fragility. Landslides lead to loss of life, disrupt supply chains, and damage critical infrastructure. Currently, early warning systems are sparse. This project aims to bridge the gap by deploying:
- Multi-source GIS data synthesis (SAR, multispectral imagery, and weather data).
- Predictive AI models for landslide susceptibility.
- Interactive GIS-based hazard dashboards providing alerts to disaster management bodies.

---

## 2. Completed Scope

### Phase 1: Foundation
- **Modular Backend Setup**: Built with Python FastAPI, featuring separation of concerns (API routes, core settings, database configurations, business logic services, and models).
- **SQLite Database Layer**: Configured with SQLAlchemy to allow modular swapping with PostgreSQL/PostGIS.
- **Frontend Dashboard**: A professional dark-themed React + Vite dashboard displaying key landslide stats, GIS placeholder, and alert logs.

### Phase 2.1: Interactive GIS Map
- **Leaflet Integration**: Replaced the static placeholder with a fully interactive map using Leaflet, `react-leaflet`, and OpenStreetMap tiles.
- **Coordinates Selection**: Captures latitude and longitude upon user clicks and places a temporary indicator marker.
- **Dark Mode Tiles**: Custom styling filters applied to OSM tiles to match the dashboard's slate theme.

### Phase 2.2: Selected Location → Backend → AOI Pipeline
- **API Endpoint**: `POST /api/v1/locations/analyze` with Pydantic validation (lat [-90, 90], lng [-180, 180], radius [0.1, 25]).
- **NER Boundary Verification**: Ray-casting algorithm validating clicks against a GeoJSON polygon of the 8 NER states stored in `backend/app/data/ner_boundary.geojson`. (Sourced from Geohacker's Indian State Boundaries dataset).
- **Geographically Scaled AOI**: Calculates a precise bounding box based on a configurable radius (default 5 km), correcting longitude scaling relative to latitude.
- **Frontend Integration**: Adds "Analyze Location" triggers, warning blocks for coordinates outside the NER, structured data tables for generated bounding boxes, and dynamic dashed rectangular bounding boxes drawn on the Leaflet map.

---

## 3. Technology Stack
- **Frontend**: React, Vite, Tailwind CSS v4, Lucide React
- **Backend**: Python 3.10+, FastAPI, Uvicorn
- **Database**: SQLite (SQLAlchemy)

---

## 4. Project Structure
```
ner-landslide-monitoring/
├── frontend/             # React + Vite (Tailwind CSS v4) application
├── backend/              # FastAPI Python backend application
│   └── app/
│       ├── main.py       # Application initialization and CORS
│       ├── api/          # Route handlers and API version controllers
│       ├── core/         # System configuration and environment settings
│       ├── models/       # Database models (SQLAlchemy)
│       ├── schemas/      # Validation schemas (Pydantic)
│       ├── services/     # Business logic layers (satellite, weather, ML)
│       └── database/     # DB connection session manager
├── ml/                   # Machine learning model pipeline placeholder (Phase 2)
├── data/                 # Spatial, weather, and raster data cache (Phase 2)
├── docs/                 # System documentation
└── README.md             # Project roadmap and run guide
```

---

## 5. Installation and Setup

### Prerequisites
- Python 3.10+
- Node.js v20+ / npm v10+

### Backend Installation & Run
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   The backend will be running at `http://localhost:8000`. You can inspect the interactive docs at `http://localhost:8000/docs`.

### Frontend Installation & Run
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open the browser at `http://localhost:5173`. The application will automatically verify and display the connection status of the backend API.

---

## 6. Future Development (Phase 2)
In the next phase, the following features will be introduced:
- **Satellite Services**: Integration of Sentinel-1 (SAR) and Sentinel-2 (optical) data using Google Earth Engine or ESA APIs to compute soil moisture index and NDVI.
- **Weather API Services**: Real-time rainfall monitoring and threshold analysis.
- **ML Susceptibility Predictor**: Models predicting landslide occurrences based on slope, aspect, rainfall intensity, and geological layers.
- **Interactive GIS Map**: Render vector and raster overlays in the dashboard using React-Leaflet or Mapbox.
- **Notification Services**: SMS/Email warning distribution.
