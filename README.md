# Gig Shield | Guidewire DevTrails Submission

Gig Shield is an intelligent emergency response and insurance workflow platform built to transform how urgent incidents, claims, and crisis situations are handled. Instead of scattered calls, delayed paperwork, and the timeless human tradition of chaos, Gig Shield centralizes everything into one smart platform.

## Live Demo and Video

- Live working link: https://guidewire-1.onrender.com
- Demo video: https://youtu.be/vHCcRVP5fNo?si=DPhJpVSMs-zXwBTl
- pitch deck link: https://drive.google.com/drive/folders/11bfbUGi1D2T872Ecc9vyL54aSE9UbjQa?usp=sharing

## Table of Contents

- Overview
- Why It Matters
- Features
- Use Cases
- Tech Stack
- Project Structure
- Run Locally
- Environment Variables
- Default Demo Credentials
- API and Route Map
- Dependencies
- AI Workflow Snapshot
- Deployment Notes

## Overview

Gig Shield connects workers, dispatch teams, and administrators in one real-time platform for:
- Incident and claim reporting
- Live delivery/case tracking
- Parametric claim trigger decisions
- Admin operations and policy management
- AI-assisted dispatch, fraud checks, and policy generation

This implementation is focused on gig-delivery insurance workflows and high-speed operational response.

## Why It Matters

Emergency and insurance workflows often fail because systems are fragmented, handoffs are slow, and decision quality drops under pressure. Gig Shield improves operational clarity by combining real-time telemetry, role-based access, and AI-assisted decisions in a single dashboard-driven product.

## Features

### User and Access
- Secure role-based login for `worker`, `company`, and `admin`
- Session hardening with protected-page login consumption and no-cache controls

### Worker Experience
- View wallet and policy status
- Buy weekly coverage tiers
- Receive pending assignments
- Accept routes and stream GPS telemetry
- Trigger claim decision flow on severe disruption

### Company Operations
- Dispatch orders manually with map coordinates
- Use AI auto-dispatch for worker assignment and reasoning

### Admin Intelligence
- Add/delete workers
- Add/delete policy options
- Generate policy tiers via AI actuarial flow
- Override premiums manually
- Monitor live order feed and claims analytics

### Smart Decision Layer
- Route risk analysis from TomTom traffic context
- Fraud scoring via neural model + explainability
- Actuarial pricing support with autoregressive baseline risk and weather signal

## Use Cases

- Insurance claim management
- Disaster and disruption response coordination
- Corporate incident and operations reporting
- Smart city service grievance routing

## Tech Stack

### Frontend
- React 18 (UMD CDN)
- ReactDOM 18 (UMD CDN)
- Babel Standalone (runtime JSX transform)
- Custom CSS (pure CSS, not Tailwind)
- GSAP for animation
- Leaflet for map interactions (company view)
- Chart.js for analytics visualizations (admin view)

### Backend
- Python + Flask
- Flask-SQLAlchemy
- APScheduler
- Requests

### Database
- PostgreSQL-compatible database via SQLAlchemy URI (`NEON_DATABASE_URL`)
- Driver: `psycopg2-binary`

### AI Layer
- LangGraph orchestration
- LangChain Core + LangChain Groq
- scikit-learn neural classifier
- SHAP explainability
- statsmodels AutoReg forecasting
- Pydantic structured outputs

### Hosting
- Render (live deployment)

## Project Structure

```text
Guidewire/
├── app/
│   ├── __init__.py
│   ├── routes.py
│   ├── db_models.py
│   ├── agent_graph.py
│   ├── agent_state.py
│   ├── fraud_agent.py
│   ├── actuary_agent.py
│   ├── dispatch_agent.py
│   ├── ml_engine.py
│   ├── services.py
│   └── config.py
├── static/
│   ├── css/styles.css
│   └── js/
│       ├── login.js
│       ├── dashboard.js
│       ├── company.js
│       └── admin.js
├── templates/
│   ├── login.html
│   ├── dashboard.html
│   ├── company.html
│   └── admin.html
├── run.py
├── background_monitor.py
├── test_fraud_nn.py
└── requirements.txt
```

## Run Locally

### 1. Clone and Enter Project

```powershell
git clone <your-repo-url>
cd Guidewire
```

### 2. Create Virtual Environment

```powershell
python -m venv .venv
```

### 3. Activate Virtual Environment (Windows PowerShell)

```powershell
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .venv\Scripts\Activate.ps1)
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create `.env` in project root:

```env
SECRET_KEY=replace-with-a-random-secret
NEON_DATABASE_URL=postgresql://<user>:<password>@<host>/<database>

# Optional but recommended for full AI/API behavior
GROQ_API_KEY=<your-groq-key>
TOMTOM_API_KEY=<your-tomtom-key>
OPENWEATHER_API_KEY=<your-openweather-key>
```

### 6. Run the Application

```powershell
python run.py
```

Open: http://127.0.0.1:5000

### 7. Optional Background Autonomous Monitor

```powershell
python background_monitor.py
```

## Environment Variables

- `SECRET_KEY` (required): Flask session signing key
- `NEON_DATABASE_URL` (required): SQLAlchemy database URI
- `GROQ_API_KEY` (optional): enables LLM-based decision modules
- `TOMTOM_API_KEY` (optional): enables real route traffic context
- `OPENWEATHER_API_KEY` (optional): enables live weather risk signal

If optional APIs are missing, the app uses fallback logic for key risk functions.

## Default Demo Credentials

On first run with an empty users table, `run.py` seeds:

- Worker: `worker1` / `1234`
- Company: `company` / `1234`
- Admin: `admin` / `1234`

## API and Route Map

### Pages
- `GET /login`
- `GET /login/<role>`
- `GET /logout`
- `GET /` (worker dashboard)
- `GET /company`
- `GET /admin`

### Worker and Delivery APIs
- `POST /buy_policy`
- `POST /api/reject_order`
- `GET /api/worker_pending_orders`
- `POST /api/start_delivery`
- `POST /api/update_gps`

### Company and Admin APIs
- `POST /api/dispatch_order`
- `POST /api/auto_dispatch`
- `GET /api/admin_live_data`
- `POST /api/update_policy`
- `POST /api/generate_tiers`

### Admin Form Actions
- `POST /admin/add_worker`
- `POST /admin/delete_worker/<id>`
- `POST /admin/add_policy`
- `POST /admin/delete_policy_option/<id>`

## Dependencies

From `requirements.txt`:

- Flask
- Flask-SQLAlchemy
- psycopg2-binary
- python-dotenv
- langgraph
- langchain-groq
- langchain-core
- requests
- APScheduler
- pandas
- numpy
- scikit-learn
- statsmodels
- shap
- pydantic
- gunicorn

Install with:

```powershell
pip install -r requirements.txt
```

## AI Workflow Snapshot

1. Route data is ingested for the active trip.
2. Parametric trigger logic checks disruption conditions.
3. If triggered, fraud analysis runs using NN + explainability.
4. Approved conditions can auto-create payout entries in claim ledger.
5. Admin can generate new policy tiers via actuarial AI pipeline.

## Deployment Notes

- Current live deployment is hosted on Render.
- For production hardening, use managed secrets, stronger auth/session controls, and production database credentials.
- `gunicorn` is available in dependencies for production serving patterns.

## Tags

#GuidewireDEVTrails #GigShield #Guidewire #Hackathon #AI #ReactJS #Flask #InsuranceTech #EmergencyResponse #Innovation #WebDevelopment