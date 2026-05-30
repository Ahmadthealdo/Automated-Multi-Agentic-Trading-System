# 📊 Automated: A Multi-Agentic Trading System

[![Python](https://img.shields.io/badge/Backend-Python-3776AB.svg?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![OpenAI Agents SDK](https://img.shields.io/badge/Backend-OpenAI_Agents_SDK-412991.svg?style=flat-square&logo=openai)](https://openai.github.io/openai-agents-python/)
[![Agent Skills](https://img.shields.io/badge/Backend-Agent_Skills-7C3AED.svg?style=flat-square&logo=openai)](https://platform.openai.com/docs)

[![HTML5](https://img.shields.io/badge/Frontend-HTML5-E34F26.svg?style=flat-square&logo=html5)](https://developer.mozilla.org/docs/Web/HTML)
[![JavaScript](https://img.shields.io/badge/Frontend-JavaScript-F7DF1E.svg?style=flat-square&logo=javascript)](https://developer.mozilla.org/docs/Web/JavaScript)
[![Tailwind CSS](https://img.shields.io/badge/Frontend-Tailwind_CSS-38BDF8.svg?style=flat-square&logo=tailwindcss)](https://tailwindcss.com/)

[![Neon PostgreSQL](https://img.shields.io/badge/Database-Neon_PostgreSQL-00E676.svg?style=flat-square&logo=postgresql)](https://neon.tech/)
[![Langfuse](https://img.shields.io/badge/Observability-Langfuse-FF5A5F.svg?style=flat-square)](https://langfuse.com/)
[![yfinance](https://img.shields.io/badge/Data-yfinance-FFCC00.svg?style=flat-square&logo=python)](https://github.com/ranaroussi/yfinance)

An elite, high-performance full-stack portal built with **Python FastAPI**, **SQLAlchemy ORM**, **Pydantic Validation**, and a **Bloomberg-inspired, industrial-utilitarian dashboard**. This platform implements a decoupled, asynchronous multi-agent orchestration architecture powered by the **OpenAI Agents SDK** and managed with **`uv`**.

---

## 🏛️ System Architecture

Rather than relying on a single monolithic prompt, this system enforces a strict separation of concerns among specialized execution nodes operating in sandboxed contexts. Data flows strictly via immutable message states.

```
       [ USER / OPERATOR ]
               │
               ▼
┌──────────────────────────────┐
│  Master Trading Desk Router  │  ◄─── [ FastAPI Web Gateway & Session Control ]
└──────────────┬───────────────┘
               │
               ▼  (Extracts parameters & timeframes)
┌──────────────────────────────┐
│ Intraday/Swing Market Analyst│  ◄─── [ technical metrics, indicators: RSI, EMA ]
└──────────────┬───────────────┘
               │
               ▼  (Proposes trading parameters)
┌──────────────────────────────┐
│      Risk Manager Agent      │  ◄─── [ compliance audits: APPROVED / REJECTED ]
└──────────────┬───────────────┘
               │
               ▼  (Deterministic Overrides applied)
┌──────────────────────────────┐
│      Neon PostgreSQL DB      │  ◄─── [ Persists transaction logs & history ]
└──────────────────────────────┘
```

### 🔹 1. Master Trading Desk Router (Orchestrator)
* **Role**: Conversational Gateway, State Initiator & Interface Controller.
* **Objective**: Ingests raw user intent, validates asset token parameters, and guides the user through execution preferences.
* **Rules**: Standardizes tickers (`AAPL` for stocks, `BTC-USD` for crypto) and restricts data fetching until both the asset identity and timeframe targets are locked in.

### 🔹 2. Intraday & Swing Market Analyst
* **Role**: Quantitative & Technical Signal Synthesizer.
* **Objective**: Consumes mathematical indicator matrices, calculates moving averages (EMA/SMA), computes momentum vectors, and outputs high-fidelity summaries.
* **Rules**: Holds zero portfolio execution or transactional decision authority; never outputs buy/sell signals directly.

### 🔹 3. Risk Manager Agent
* **Role**: Capital Preservation & Compliance Audit Guardrail.
* **Objective**: Final automated gatekeeper that audits proposed operations against structural safety rules.
* **Rules**: Prefixes audits with `[APPROVED]` or `[REJECTED]` and appends a single sentence of quantitative compliance justification.

---

## ⚡ Key Features

* **Premium Bloomberg-Inspired UI**: Radial dark slate background (`#0B0F17`), sleek panel styling (`#131C2E`), and absolute neon-accent high-contrast color codes.
* **Interactive Live SVG Candle Charting**: Fetches actual real-time price candlesticks (using `yfinance`) and dynamically wicks, scales, and plots candles inside the SVG container with a **10-second polling live update**.
* **Quick-Select Asset Badges**: Instantly targets leading tech assets (`AAPL`, `NVDA`, `TSLA`, `MSFT`) and cryptocurrencies (`BTC-USD`, `ETH-USD`, `SOL-USD`) at the click of a button.
* **Strict Parameter Overrides**: Integrates real-time compliance blocks. If the Risk Manager issues a `[REJECTED]` verdict, the portal forces a strict `HOLD` override and updates position sizing allocations to `0%` to preserve capital.
* **State-of-the-Art Langfuse Telemetry**: Tracks global traces the moment the user interacts with the desk, nests execution spans for each agent run, and captures final database insertion payloads.
* **Secure Operator Portal**: Full SQLAlchemy-backed authentication featuring custom-validated sign-ups (Pakistani/International cell validation, flexible 6+ character passwords) and password hashing with `passlib[bcrypt]`.

---

## 📊 Dynamic Strategy Matrix

Data lookbacks and execution calculations automatically shift based on the strategy selected in the dashboard:

| Strategy Category | Timeframe | Lookback | Data Interval | Primary Indicators | Exit Bounds (Stop Loss / Take Profit) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Intraday Scalp** | 15-Minute (`15m`) | 7 Days (`7d`) | `15m` | 9-EMA, 21-EMA, RSI (14) | `-1.0% / +2.0%` |
| **Intraday Swing** | 1-Hour (`1h`) | 30 Days (`30d`) | `1h` | 9-EMA, 21-EMA, RSI (14) | `-2.5% / +5.0%` |
| **Medium Swing** | 4-Hour (`4h`) | 60 Days (`60d`) | `4h` | 50-MA, MACD, RSI (14) | `-4.0% / +8.0%` |
| **Macro Position** | 1-Day (`1d`) | 180 Days (`180d`) | `1d` | 50-MA, 200-MA, Macro RSI | `-8.0% / +15.0%` |

---

## ⚙️ Installation & Setup

Ensure you have **Python 3.12+** and **`uv`** installed on your system.

### 1. Clone & Initialize Workspace
```bash
git clone https://github.com/Ahmadthealdo/Automated-Multi-Agentic-Trading-System.git
cd Automated-Multi-Agentic-Trading-System
```

### 2. Install Project Dependencies
Run the following `uv` command to create the virtual environment and install all web-hosting, validation, and multi-agent libraries:
```bash
uv pip install -r pyproject.toml
# Or install explicitly:
uv add fastapi uvicorn "pydantic[email]" "passlib[bcrypt]" psycopg sqlalchemy yfinance openai langfuse
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Relational Neon PostgreSQL Connection String
DATABASE_URL=postgresql://<user>:<password>@<host>/<database>?sslmode=require

# OpenAI API Key for Multi-Agent Brain
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Langfuse Telemetry Tracing Keys
LANGFUSE_PUBLIC_KEY=pk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-lf-xxxxxxxxxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 4. Database Setup & Migrations
Upon application startup, FastAPI dynamically verifies relational tables and automatically handles any database column migrations (such as upgrading `mobile_number` to `verified_phone` on Neon PostgreSQL), making database setup 100% zero-configuration.

---

## 🚀 Running the Application

### Start the FastAPI Dev Server
Launch the application locally in reloading development mode:
```bash
uvicorn main:app --reload
```
The application will boot and host the interactive portal locally at **`http://127.0.0.1:8000`**.

### 🧪 Programmatic Verification Run
Run our end-to-end multi-agent pipeline validation test in your terminal to verify databases, indicators, and agent outputs instantly:
```bash
python .agents/brain/8169d2e7-195f-482a-bf14-b5bf777313c9/scratch/validate_system.py
```

---

## 📁 File Structure

```
├── .agents/                    # System Agent workspace instructions & skills
├── static/
│   ├── app.js                  # Scaled SVG candle drawer & client logic
│   └── style.css               # Utilitarian Bloomberg layout styles
├── templates/                  # Frontend views
├── index.html                  # Core single-page operator dashboard
├── main.py                     # FastAPI server routes & multi-agent execution pipeline
├── schemas.py                  # Pydantic validation boundaries & schemas
├── tools.py                    # yfinance quantitative extraction tools
├── pyproject.toml              # UV dependency declarations
└── README.md                   # System documentation
```

---

---

## 👥 Authors & Contributors

* **Abdul Qadeer Khan**
* **Ahmad Abdullah**

---

## 🛡️ License

This project is licensed under the Apache 2.0 License - see the [LICENSE](file:///mnt/FA68E41D68E3D683/Agentic%20_AI/Automated-Multi-Agentic-Trading-System/LICENSE) file for details.
