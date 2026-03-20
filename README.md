<div align="center">

<img src="https://img.shields.io/badge/GigShield-AI%20Insurance-6366f1?style=for-the-badge&logo=shield&logoColor=white" alt="GigShield"/>

# 🛡️ GigShield

### AI-Powered Parametric Insurance for India's Gig Economy

*Automated income protection for delivery partners — no forms, no adjusters, no delays.*

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6B35?style=flat-square&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Groq](https://img.shields.io/badge/Groq-Llama%203-F55036?style=flat-square&logo=groq&logoColor=white)](https://groq.com)
[![PostgreSQL](https://img.shields.io/badge/Neon-PostgreSQL-00E699?style=flat-square&logo=postgresql&logoColor=white)](https://neon.tech)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 🚨 The Problem

India's gig economy runs on millions of delivery partners (Zomato, Swiggy, Zepto, etc.) who face unpredictable external disruptions every single day. Extreme weather, severe gridlock, AQI spikes, and road closures can wipe out **20–30% of their monthly earnings** — and they have zero safety net.

> **GigShield fixes that.** Instant, automated, AI-verified micro-payouts. No paperwork. No waiting.

---

## 💡 What It Does

GigShield is a **Neuro-Symbolic, Agentic AI** parametric insurance platform that:

- 📊 **Prices risk dynamically** using an Autoregressive (AR) model + live weather forecasts
- 🤖 **Monitors every delivery** via a LangGraph multi-agent orchestrator
- 🗺️ **Evaluates live traffic** using the TomTom Routing API in real-time
- 🧠 **Detects fraud** with a Neural Network + SHAP explainability layer
- ⚡ **Executes micro-payouts instantly** (e.g., ₹250) when a legitimate disruption is confirmed
- 📋 **Logs everything immutably** in an admin financial ledger

> Strictly covers **income loss only** — no health, life, or vehicle repair coverage.

---

## 🏗️ System Architecture

The platform operates as a **three-sided marketplace** (Admin · Worker · Company) powered by a fully autonomous AI backend across 5 phases:

```
╔══════════════════════════════════════════════════════════════╗
║           PHASE 1 — RISK ASSESSMENT & POLICY GENERATION      ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [ Admin ] ──clicks "Run XAI Actuary"──►                     ║
║                                                              ║
║  [ AR Model ] ◄── [ Historical Risk DB ]                     ║
║       │                                                      ║
║       ▼  (Baseline Risk Score)                               ║
║  [ Groq Llama 3 LLM ] ◄── [ OpenWeather API ]               ║
║       │                                                      ║
║       ▼  (XAI Explanations + Tiers)                          ║
║  [ DB: Basic / Standard / Premium Policy Options ]           ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║           PHASE 2 — COVERAGE ACQUISITION                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [ Worker App ] ──reads XAI reasoning──►                     ║
║  [ Worker clicks "Buy Cover" ]                               ║
║       │                                                      ║
║       ▼                                                      ║
║  [ Wallet Deducted ] ──► [ Active Weekly Policy Created ]    ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║           PHASE 3 — DISPATCH & ORCHESTRATION                 ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [ Delivery Platform Simulator ] ──dispatches coordinates──► ║
║  [ Pending Order Queue ]                                     ║
║       │                                                      ║
║       ▼  (Worker clicks "Accept & Start GPS")                ║
║  [ LangGraph Multi-Agent Orchestrator ] ◄── WAKES UP         ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║           PHASE 4 — LIVE TELEMETRY & RISK EVALUATION         ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [ TomTom Routing API ] ──polyline + delays──►               ║
║  [ Worker JS ] ──iterates polyline──► [ Live GPS Pings ]     ║
║       │                                                      ║
║       ▼  (Delay > 30 mins OR Road Closed?)                   ║
║  ┌────┴────┐                                                 ║
║  YES       NO                                                ║
║  │         └──► [ Delivery Completed — No Payout ]           ║
║  ▼                                                           ║
║  [ Fraud Agent ] ──Neural Net checks speed & deviation──►    ║
║                                                              ║
╠══════════════════════════════════════════════════════════════╣
║           PHASE 5 — AUTOMATED CLAIM EXECUTION                ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  [ Fraud Score < 0.5? ]                                      ║
║  ┌────┴────┐                                                 ║
║  YES       NO                                                ║
║  │         └──► [ Claim DENIED & Flagged for Review ]        ║
║  ▼                                                           ║
║  [ Smart Ledger Agent ]                                      ║
║  [ Worker Wallet Credited ₹250 ]                             ║
║  [ Immutable Log → Admin Ledger ]                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

## 🤖 AI Agent Stack

| Agent | Role | Technology |
|---|---|---|
| **XAI Actuary Agent** | Generates weekly policy tiers with human-readable justifications | Groq Llama 3 8B + Statsmodels AR |
| **LangGraph Orchestrator** | Coordinates the full delivery lifecycle across 3 nodes | LangGraph StateGraph |
| **Fraud Detection Agent** | Validates claims using Neural Net + SHAP explainability | Scikit-learn MLP + SHAP + Groq |
| **Smart Ledger Agent** | Executes micro-payouts and logs to immutable ledger | Flask + SQLAlchemy |

### LangGraph Node Flow

```
ingest_data ──► route_analysis ──► (conditional) ──► fraud_check ──► END
                                        │
                                   (no trigger)
                                        │
                                       END
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, Flask |
| **AI Orchestration** | LangGraph, LangChain |
| **LLM** | Groq (Llama 3 8B) |
| **ML / XAI** | Scikit-learn (MLP Neural Net), Statsmodels (AutoReg), SHAP |
| **Database** | Neon Serverless PostgreSQL, SQLAlchemy ORM |
| **Traffic API** | TomTom Routing & Traffic API |
| **Weather API** | OpenWeather API |
| **Frontend** | HTML5, Tailwind CSS, Vanilla JavaScript |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/gigshield.git
cd gigshield
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
NEON_DATABASE_URL=postgresql://user:password@host/dbname

GROQ_API_KEY=your_groq_api_key_here
TOMTOM_API_KEY=your_tomtom_api_key_here
OPENWEATHER_API_KEY=your_openweather_api_key_here
```

> **Note:** The app runs in graceful fallback mode if API keys are missing — useful for local demos without live API access.

### 5. Run the application

```bash
python run.py
```

The app will start at `http://localhost:5000` and auto-seed three demo accounts.

---

## 👤 Demo Accounts

| Role | Username | Password | Access |
|---|---|---|---|
| 🔧 Admin | `admin` | `1234` | Policy generation, live tracking, financial ledger |
| 🛵 Worker | `worker1` | `1234` | Buy coverage, accept orders, receive payouts |
| 🏢 Company | `company` | `1234` | Dispatch delivery orders with coordinates |

---

## 📁 Project Structure

```
gigshield/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Environment config
│   ├── db_models.py         # SQLAlchemy models (User, Policy, Order, Ledger)
│   ├── routes.py            # All Flask routes & API endpoints
│   ├── services.py          # TomTom & OpenWeather API integrations
│   ├── actuary_agent.py     # XAI Actuary — AR model + Groq LLM pricing
│   ├── agent_graph.py       # LangGraph orchestrator (3-node workflow)
│   ├── agent_state.py       # LangGraph ClaimState TypedDict
│   ├── fraud_agent.py       # Fraud detection — Neural Net + SHAP + LLM
│   └── ml_engine.py         # PricingAutoregressor & FraudNeuralNet classes
├── templates/
│   ├── login.html           # Auth page
│   ├── dashboard.html       # Worker portal
│   ├── company.html         # Delivery dispatch simulator
│   └── admin.html           # Admin control center + live map
├── run.py                   # App entry point + DB seeder
├── requirements.txt
└── .env                     # (not committed) API keys & DB URL
```

---

## 🔑 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/generate_tiers` | Admin triggers XAI Actuary to regenerate policy tiers |
| `POST` | `/buy_policy` | Worker purchases weekly coverage |
| `POST` | `/api/dispatch_order` | Company dispatches a delivery with GPS coordinates |
| `POST` | `/api/start_delivery` | Worker accepts order — triggers LangGraph pipeline |
| `POST` | `/api/update_gps` | Live GPS ping from worker's device |
| `POST` | `/api/reject_order` | Worker rejects a pending delivery |

---

## 🧠 How the Fraud Detection Works

1. **Neural Network** (Scikit-learn MLP) scores the claim on 4 telemetry features:
   - Live speed (kph)
   - Route deviation (km)
   - Time of day
   - Historical average speed

2. **SHAP** generates feature importance values explaining *why* the model scored it that way.

3. **Groq Llama 3** translates the raw SHAP output into a single human-readable audit sentence.

4. If `fraud_score < 0.5` → claim **APPROVED**, payout executed instantly.  
   If `fraud_score ≥ 0.5` → claim **FLAGGED**, logged for admin review.

---

## 📊 Database Models

```
User            — workers, admins, companies with wallet balances
PolicyOption    — AI-generated Basic / Standard / Premium tiers
WeeklyPolicy    — active coverage purchased by a worker
DeliveryOrder   — dispatched orders with live GPS coordinates
ClaimLedger     — immutable record of every payout executed
```

---

## 🌐 External API Dependencies

| API | Purpose | Fallback |
|---|---|---|
| **TomTom Routing** | Live polyline, delay calculation, speed data | Simulated gridlock scenario |
| **OpenWeather** | 5-day forecast for actuarial risk surcharge | "Heavy Rain" mock response |
| **Groq (Llama 3)** | Policy XAI descriptions + fraud audit logs | Rule-based fallback text |

---

<div align="center">

Built for India's 15 million+ gig workers.

</div>
