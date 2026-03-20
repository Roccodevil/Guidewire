# 🛡️ GigShield: AI-Powered Parametric Insurance for the Gig Economy

**An Agentic AI platform providing automated, transparent income protection for India's platform-based delivery partners.**

---

## The Problem

India's gig economy relies on millions of delivery partners (Zomato, Swiggy, Zepto, etc.) who face unpredictable external disruptions. Extreme weather, severe pollution (AQI spikes), and social disruptions (local strikes, unplanned curfews, severe gridlock) can cause them to lose **20–30% of their monthly earnings**. Currently, gig workers bear the full financial loss of these uncontrollable events with zero safety net.

---

## Our Solution

**GigShield** is a Neuro-Symbolic, Agentic AI-enabled parametric insurance platform strictly designed to protect **income loss**. We utilize a **LangGraph Multi-Agent Orchestrator** to monitor live environmental APIs (TomTom Traffic, OpenWeather) during a delivery. If a worker gets trapped in severe gridlock or heavy flooding, our AI instantly verifies the event, checks for fraud using Neural Networks, and executes an automated micro-payout directly to their wallet — no claims forms, no adjusters, no delays.

### Core Design Constraints

1. **Strict Income Protection:** Covers lost time/earnings only (no health, life, or vehicle repair coverage).
2. **Weekly Pricing Model:** Actuarial premiums are calculated dynamically on a 7-day cycle to match the exact payout cycle of Indian gig workers.

---

## System Workflow

The platform operates as a three-sided marketplace (Admin, Worker, Company) powered by an autonomous AI backend.

```
=============================================================================
PHASE 1: RISK ASSESSMENT & POLICY GENERATION
=============================================================================
[ Admin Control Center ]
│
▼ (1. Clicks "Run XAI Actuary")
│
[ Autoregressive (AR) Model ] <------- [ Historical Risk DB ]
│
▼ (2. Baseline Risk Score)
│
[ Groq Llama 3 LLM ] <---------------- [ OpenWeather API Forecast ]
│
▼ (3. Generates Tiers & XAI Explanations)
│
[ Database: Policy Options (Basic, Standard, Premium) ]

=============================================================================
PHASE 2: COVERAGE ACQUISITION
=============================================================================
[ Database: Policy Options ]
│
▼ (4. Reads XAI Reasoning)
│
[ Gig Worker App ]
│
▼ (5. Clicks "Buy Cover")
│
[ Wallet Balance Deducted ] ---------> [ Database: Active Weekly Policy ]

=============================================================================
PHASE 3: DISPATCH & ORCHESTRATION
=============================================================================
[ Delivery Platform Simulator (Zomato/Swiggy) ]
│
▼ (6. Dispatches Real Coordinates)
│
[ Pending Order Queue ]
│
▼ (7. Worker Clicks "Accept & Start GPS")
│
[ LangGraph Multi-Agent Orchestrator ] (Wakes Up)

=============================================================================
PHASE 4: LIVE TELEMETRY & RISK EVALUATION
=============================================================================
[ LangGraph Orchestrator ]
│
├──> [ TomTom Routing API ] (8. Fetches exact road polyline & delays)
│
▼ [ Worker App ] (9. JS script iterates through TomTom polyline)
│
▼
[ Live GPS Pings ] ------------------> [ Admin Live Tracking Dashboard ]
│
▼ (10. AI evaluates traffic conditions)
│
[ Delay > 30 mins or Road Closed? ]
│                       │
▼ (YES)                 ▼ (NO)
│                       │
[ Fraud Agent ]          [ Delivery Completed ]
│                        (No payout needed)
▼ (11. Neural Net checks speed & route deviation vs. API)

=============================================================================
PHASE 5: AUTOMATED CLAIM EXECUTION
=============================================================================
[ Fraud Agent Validation ]
│
[ Fraud Score < 0.5? ]
│                       │
▼ (YES - Legitimate)    ▼ (NO - Spoofing Detected)
│                       │
[ Smart Ledger Agent ]   [ Claim Denied & Flagged for Review ]
│
▼ (12. Micro-payout executed instantly)
│
[ Worker Wallet Credited (e.g., ₹250) ]
│
▼
[ Immutable Log Saved to Admin Ledger ]
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | Python Flask |
| AI / Multi-Agent Engine | LangGraph, LangChain, Groq (Llama 3 8B) |
| Machine Learning / XAI | Scikit-Learn (Neural Networks), Statsmodels (Autoregressor), SHAP |
| Database | Neon (Serverless PostgreSQL), SQLAlchemy ORM |
| External APIs | TomTom Traffic & Routing API, OpenWeather API |
| Frontend | HTML5, Tailwind CSS, Vanilla JavaScript |

---

## Setup & Installation

**1. Clone the repository**

```bash
git clone https://github.com/yourusername/gig-insurance-platform.git
cd gig-insurance-platform
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file in the root directory:

```env
DATABASE_URL=your_neon_postgresql_connection_string
GROQ_API_KEY=your_groq_api_key
TOMTOM_API_KEY=your_tomtom_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
SECRET_KEY=your_flask_secret_key
```

**5. Run the application**

```bash
python run.py
```

The app will be available at `http://localhost:5000`.

---

## User Roles

| Role | Access | Key Actions |
|---|---|---|
| Admin | `/admin` | Run XAI Actuary, monitor live GPS, view financial ledger |
| Gig Worker | `/dashboard` | Buy weekly cover, accept orders, track wallet |
| Company | `/company` | Dispatch delivery orders with coordinates |

---

## Project Structure

```
├── app/
│   ├── actuary_agent.py     # XAI Actuary Agent (AR Model + Llama 3)
│   ├── agent_graph.py       # LangGraph Multi-Agent Orchestrator
│   ├── agent_state.py       # Shared agent state definitions
│   ├── config.py            # App configuration & env vars
│   ├── db_models.py         # SQLAlchemy ORM models
│   ├── fraud_agent.py       # Neural Net fraud detection agent
│   ├── ml_engine.py         # ML model training & inference
│   ├── routes.py            # Flask route handlers
│   └── services.py          # Business logic & API integrations
├── templates/               # HTML templates (Tailwind CSS)
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── test_fraud_nn.py         # Fraud neural network tests
```

---
