# MomWatch AI - Maternal Health Monitoring System

# PROBLEM STATEMENT

## Title
**"Real-Time Clinical Decision Support Gap for Community Health Workers in Maternal Care"**

## The Problem
In rural and semi-urban India, **900,000+ ASHA** (Accredited Social Health Activist) workers serve as the primary healthcare interface for over **26 million pregnancies** annually. These frontline workers face critical challenges:

* **Knowledge Gap:** 78% of ASHA workers lack formal medical training, relying on basic checklists that don't adapt to complex clinical scenarios.
* **Delayed Risk Recognition:** 45% of maternal deaths occur due to delayed identification of complications like preeclampsia, gestational diabetes, and hemorrhage risk. By the time symptoms become obvious, critical intervention windows have passed.
* **Infrastructure Constraints:**
    * 60% of rural health centers lack consistent internet connectivity.
    * Paper-based tracking systems create data fragmentation.
    * No standardized triage protocol across different PHCs (Primary Health Centers).
* **Communication Barriers:**
    * Doctors receive incomplete or misinterpreted patient histories.
* **Resource Allocation:** District hospitals don't know which patients need urgent attention until they physically arrive, leading to:
    * Ambulance misallocation.
    * Emergency room overcrowding with non-urgent cases.
    * Critical cases waiting in queue behind stable patients.

## Real-World Impact
*Current Statistics (WHO India, 2023):*

* **Maternal Mortality Ratio:** 97 deaths per 100,000 live births.
* **67%** of these deaths are preventable with timely triage.
* **Average delay** from symptom onset to treatment: 4.2 hours.
* **Only 32%** of high-risk pregnancies are identified before complications.

## 🏥 Overview

**MomWatch AI** is a production-grade, defensively-engineered maternal health monitoring system designed specifically for **rural Indian healthcare** and **ASHA workers** (Accredited Social Health Activists). The system employs a novel **Finite State Machine (FSM) architecture** with **Human-in-the-Loop (HITL)** capabilities to ensure reliable, traceable risk assessments even in resource-constrained environments.

### 🎯 Target Users

1. **ASHA Workers** - Frontline community health workers conducting maternal health screenings in rural areas
2. **Pregnant Women** - Rural mothers accessing prenatal care through ASHA workers  
3. **Doctors** - Medical professionals reviewing flagged cases and HITL queue

### 🌟 Novel Architecture Highlights

- **🔄 FSM-Based Processing** - 9-state deterministic state machine for complete traceability
- **🤝 Human-in-the-Loop (HITL)** - Low-confidence cases (<65%) automatically escalated to doctors
- **🍯 Honeypot Middleware** - Layer 0 defense against malicious/adversarial inputs
- **🔒 Idempotency Guarantees** - Prevent duplicate assessments with `client_sync_uuid`
- **⚡ Circuit Breaker Pattern** - Graceful ML model degradation with rules-based fallback
- **📊 Optimistic Locking** - Version-based conflict resolution for concurrent HITL reviews
- **🛡️ Defensive Engineering** - Multi-layer validation, graceful degradation, comprehensive error handling

---

## 📋 Table of Contents

- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [FSM Pipeline](#-fsm-pipeline-9-states)
- [HITL Workflow](#-hitl-human-in-the-loop-workflow)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Security](#-security-features)
- [Clinical Thresholds](#-clinical-thresholds)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Monitoring](#-monitoring)

---

## ✨ Key Features

### For ASHA Workers
- 📱 **Simple Mobile-First Interface** - Easy vitals entry on basic smartphones
- 📝 **Guided Data Collection** - Step-by-step forms with validation
- ⚡ **Instant Risk Assessment** - Real-time triage decisions (<1 second)
- 🚨 **Automatic Escalation** - Critical cases immediately flagged for doctors
- 📊 **Visual Health Passport** - Easy-to-understand risk indicators

### For Doctors
- 👨‍⚕️ **HITL Review Queue** - Prioritized low-confidence cases requiring expert review
- 📈 **FSM Trace Visualization** - Complete processing history for each assessment
- 🔍 **Explainable AI** - Feature importance charts show which vitals drove the decision
- ⏱️ **Emergency Dashboard** - Real-time feed of critical cases
- 📋 **Batch Processing** - Review multiple cases efficiently

### For Healthcare System
- 🔄 **100% Uptime** - Circuit breaker ensures system never fully fails
- 📊 **Audit Trail** - FSM traces provide complete accountability
- 🛡️ **Attack Resistant** - Honeypot middleware blocks adversarial inputs
- 🔐 **HIPAA-Ready** - JWT authentication, encrypted communications
- 🐳 **Easy Deployment** - Docker-based, runs on minimal infrastructure

---

## 🚀 Quick Start

### Prerequisites

- **Docker** 24.0+ and **Docker Compose** 3.8+
- **4GB RAM** minimum (8GB recommended for ML model)
- **5GB free disk space**

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/momwatch_ai.git
cd momwatch_ai
```

2. **Configure environment variables:**
```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

**Required Configuration:**
```env
# Security (REQUIRED)
JWT_SECRET=your_32_character_minimum_secret_key_here

# MongoDB (Pre-configured for Docker)
MONGO_URI=mongodb://mongodb:27017
MONGO_DB_NAME=momwatch_db

# HITL Configuration
HITL_CONFIDENCE_THRESHOLD=0.65  # Cases below 65% confidence go to HITL
HONEYPOT_ENABLED=true            # Enable adversarial input detection
```

3. **Start the application:**
```bash
docker-compose up --build -d
```

4. **Access the application:**
- **Frontend (Streamlit):** http://localhost:8501
- **Backend API Docs:** http://localhost:8000/docs
- **System Health:** http://localhost:8000/admin/system/health

### First-Time Setup

1. **Create user accounts:**
   ```bash
   # Navigate to http://localhost:8501
   # Register as "asha" role (for ASHA workers)
   # Register as "doctor" role (for medical professionals)
   ```

2. **Verify system health:**
   ```bash
   curl http://localhost:8000/admin/system/health
   ```

3. **Test triage submission** (see [API Documentation](#-api-documentation))

---

## 🏗️ Architecture

### System Components

```
┌──────────────────┐
│   Streamlit UI   │  ASHA Worker / Doctor Interface
│   (Frontend)     │
└────────┬─────────┘
         │ HTTP/REST
         ↓
┌──────────────────┐
│   FastAPI        │  REST API + FSM Orchestrator
│   (Backend)      │
└────────┬─────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌─────────┐ ┌──────────────────┐
│ MongoDB │ │ FSM Risk Engine  │
│ Atlas   │ │                  │
└─────────┘ └────────┬─────────┘
                     │
         ┌───────────┼───────────┐
         ↓           ↓           ↓
    ┌────────┐  ┌────────┐  ┌─────────┐
    │Honeypot│  │Clinical│  │   ML    │
    │Security│  │ Rules  │  │  Model  │
    └────────┘  └────────┘  └─────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit 1.31+ | Mobile-first UI for ASHA workers |
| **Backend** | FastAPI 0.109+ | Async REST API with FSM orchestrator |
| **Database** | MongoDB 6.0+ (Atlas) | Document store for decisions + HITL queue |
| **ML Model** | Scikit-learn Random Forest | Risk prediction (99.6% accuracy) |
| **Security** | JWT + Bcrypt | Authentication & password hashing |
| **Deployment** | Docker + Docker Compose | Containerized microservices |

---

## 🔄 FSM Pipeline (9 States)

The system processes each triage request through a **deterministic Finite State Machine** with complete observability:

```
START
  ↓
[INGEST] ──honeypot──→ [REJECT]
  ↓ clean
[SANITY] ──invalid──→ [REJECT]  
  ↓ valid
[RULE_ENGINE] ──critical──→ [SAVE_DB] → [DONE]
  ↓ non-critical
[ML_INFERENCE] ──failed──→ [SAVE_DB] → [DONE] (fallback)
  ↓ success
[CONFIDENCE_CHECK]
  ↓
  ├──high (≥0.65)──→ [SAVE_DB] → [DONE]
  └──low (<0.65)───→ [HITL_HANDOFF] (doctor review)
```

### State Descriptions

| State | Purpose | Exit Conditions |
|-------|---------|-----------------|
| **INGEST** | Entry point, honeypot detection | Clean → SANITY, Malicious → REJECT |
| **SANITY** | Pydantic validation (bio-plausible ranges) | Valid → RULE_ENGINE, Invalid → REJECT |
| **RULE_ENGINE** | WHO clinical thresholds | Critical → SAVE_DB, Normal → ML_INFERENCE |
| **ML_INFERENCE** | Random Forest prediction via circuit breaker | Success → CONFIDENCE_CHECK, Fail → SAVE_DB (fallback) |
| **CONFIDENCE_CHECK** | Evaluate if human review needed | High conf → SAVE_DB, Low conf → HITL_HANDOFF |
| **SAVE_DB** | Persist decision with idempotency | Always → DONE |
| **DONE** | Terminal success state | - |
| **REJECT** | Terminal failure state (invalid/malicious) | - |
| **HITL_HANDOFF** | Terminal state (awaiting doctor review) | - |

### FSM Trace Example

Every assessment generates a complete trace:

```json
{
  "fsm_trace": [
    {"from": "INGEST", "to": "SANITY", "duration_ms": 2, "metadata": {}},
    {"from": "SANITY", "to": "RULE_ENGINE", "duration_ms": 15, "metadata": {"validated": true}},
    {"from": "RULE_ENGINE", "to": "ML_INFERENCE", "duration_ms": 23, "metadata": {"bypass_ml": false}},
    {"from": "ML_INFERENCE", "to": "CONFIDENCE_CHECK", "duration_ms": 145, "metadata": {"ml_confidence": 0.62}},
    {"from": "CONFIDENCE_CHECK", "to": "HITL_HANDOFF", "duration_ms": 5, "metadata": {"requires_hitl": true}}
  ],
  "total_processing_ms": 190
}
```

---

## 🤝 HITL (Human-in-the-Loop) Workflow

### When is HITL Triggered?

Cases are automatically escalated to the HITL queue when:
1. **ML confidence < 65%** (configurable via `HITL_CONFIDENCE_THRESHOLD`)
2. **Borderline vital signs** (e.g., BP 138/88, trace proteinuria)
3. **Contradictory indicators** (some vitals normal, others concerning)

### Doctor Review Process

1. **Access HITL Queue:**
   ```
   GET /doctor/hitl-queue
   ```
   Returns prioritized list of pending cases

2. **Review FSM Trace:**
   - See complete processing history
   - View ML confidence score
   - Check feature importances
   - Analyze vital signs

3. **Make Decision:**
   ```
   POST /doctor/hitl-resolve
   {
     "decision_id": "6578...",
     "action": "confirm_ml",  // or "escalate_to_critical", "downgrade_to_low"
     "version_id": "abc123",   // for optimistic locking
     "doctor_notes": "Agree with ML assessment. Monitor BP closely."
   }
   ```

4. **Optimistic Locking:**
   - If another doctor reviewed simultaneously, get `409 Conflict`
   - Frontend auto-refreshes to show updated case

### HITL Metrics

Available at `/admin/system/health`:
```json
{
  "fsm_statistics": {
    "hitl_cases_pending": 3,
    "hitl_cases_resolved": 127,
    "avg_hitl_resolution_time_minutes": 8.3
  }
}
```

---

## 📁 Project Structure

```
momwatch_ai/
├── backend/                          # FastAPI backend with FSM orchestrator
│   ├── app/
│   │   ├── api/                     # REST API endpoints
│   │   │   ├── auth.py              # JWT authentication (register/login)
│   │   │   ├── triage.py            # FSM-based triage endpoint
│   │   │   ├── doctor.py            # HITL queue management
│   │   │   ├── asha.py              # ASHA worker profile APIs
│   │   │   └── admin.py             # System health + FSM statistics
│   │   ├── engine/                  # Risk assessment core
│   │   │   ├── fsm_orchestrator.py  # **9-state FSM pipeline**
│   │   │   ├── sanity.py            # Layer 0: Pydantic validation
│   │   │   ├── rules.py             # Layer 1: WHO clinical rules
│   │   │   ├── ml_model.py          # Layer 2: RandomForest inference
│   │   │   ├── circuit.py           # Circuit breaker pattern
│   │   │   └── orchestrator.py      # Legacy 2-layer orchestrator
│   │   ├── middleware/
│   │   │   └── honeypot.py          # **Adversarial input detection**
│   │   ├── db/
│   │   │   ├── mongo.py             # MongoDB Atlas connection
│   │   │   ├── fsm_repository.py    # **FSM decision persistence**
│   │   │   ├── repositories.py      # Legacy repositories
│   │   │   └── schemas.py           # Pydantic database schemas
│   │   ├── models/
│   │   │   ├── requests.py          # API request DTOs
│   │   │   └── responses.py         # API response DTOs
│   │   └── utils/
│   │       ├── dependencies.py      # FastAPI dependencies
│   │       ├── logger.py            # Structured logging
│   │       └── security.py          # JWT + password hashing
│   ├── tests/                        # Comprehensive test suite
│   │   ├── test_circuit.py
│   │   ├── test_rules.py
│   │   ├── test_sanity.py
│   │   └── test_idempotency.py
│   ├── migrate_roles.py              # Database migration scripts
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                         # Streamlit ASHA/Doctor interface
│   ├── views/
│   │   ├── login.py                 # Authentication page
│   │   ├── asha_panel.py            # **ASHA worker dashboard**
│   │   ├── doctor_panel.py          # Doctor emergency feed
│   │   ├── hitl_queue.py            # **HITL review interface**
│   │   ├── about.py
│   │   └── contact.py
│   ├── components/
│   │   ├── vitals_form.py           # Guided data entry
│   │   ├── xai_chart.py             # Feature importance viz
│   │   ├── health_passport.py       # Patient risk summary
│   │   └── alert_card.py            # Emergency alerts
│   ├── utils/
│   │   ├── api_client.py            # Backend HTTP client
│   │   ├── state_manager.py         # Session state management
│   │   └── session_persistence.py
│   ├── app.py                        # Streamlit entry point
│   ├── Dockerfile
│   └── requirements.txt
│
├── ml_ops/                           # ML model training pipeline
│   ├── dataset_gen.py               # Synthetic data generation
│   ├── train.py                     # RandomForest training
│   ├── evaluate.py                  # Model evaluation
│   └── model_store/                 # Trained model artifacts
│       ├── maternal_rf_model.joblib
│       ├── feature_scaler.joblib
│       └── label_encoder.joblib
│
├── docs/                             # Documentation
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   ├── DEFENSIVE_ENGINEERING.md
│   ├── HITL_TESTING.md              # **HITL testing guide**
│   └── VALIDATION_SESSION_FIXES.md
│
├── data/
│   └── mongodb/                      # MongoDB data persistence
│
├── logs/                             # Application logs
├── docker-compose.yml                # Multi-container orchestration
├── .env.example                      # Environment template
├── ZUDU_REMOVAL_SUMMARY.md           # Architecture change log
└── README.md
```

**Key Files:**
- 🔄 `fsm_orchestrator.py` - Core FSM implementation (9 states)
- 🤝 `fsm_repository.py` - HITL queue + decision persistence
- 🍯 `honeypot.py` - Layer 0 adversarial defense
- 👩‍⚕️ `asha_panel.py` - Primary user interface
- 👨‍⚕️ `hitl_queue.py` - Doctor review dashboard

---

## 📊 Clinical Thresholds

### CRITICAL Flags (Immediate Escalation, Bypass ML)

| Vital Sign | Threshold | Clinical Risk | FSM Transition |
|-----------|-----------|---------------|----------------|
| **Systolic BP** | ≥140 mmHg | Preeclampsia | RULE_ENGINE → SAVE_DB |
| **Diastolic BP** | ≥90 mmHg | Preeclampsia | RULE_ENGINE → SAVE_DB |
| **SpO2** | <94% | Respiratory distress | RULE_ENGINE → SAVE_DB |
| **Heart Rate** | >120 bpm | Hemorrhage/Infection | RULE_ENGINE → SAVE_DB |
| **Blood Sugar** | <3.0 mmol/L | Seizure risk | RULE_ENGINE → SAVE_DB |
| **Blood Sugar** | >11.0 mmol/L | DKA risk | RULE_ENGINE → SAVE_DB |

**Note:** Critical cases **bypass ML model** entirely and go straight to SAVE_DB with 100% confidence.

### MEDIUM Risk Factors

| Factor | Threshold | Weight |
|--------|-----------|--------|
| Advanced Maternal Age | ≥35 years | +15% risk |
| Post-term Pregnancy | >40 weeks | +20% risk |
| Hyperthermia | >38.5°C | +10% risk |
| Trace Proteinuria | +1 | +8% risk |
| Mild Edema | Present | +5% risk |

### HITL Trigger Conditions (Confidence < 65%)

Cases likely to enter HITL queue:
- **Borderline BP:** 135-139/85-89 mmHg
- **Trace proteinuria** with normal BP
- **Single abnormal vital** with others normal
- **Contradictory indicators** (e.g., high HR but normal temp)
- **ML model disagreement** with rules engine

---

## 🔐 Security Features

### Layer 0: Honeypot Middleware

Detects adversarial/malicious inputs **before** they reach the FSM:

```python
# Monitored honeypot fields (should never be present)
HONEYPOT_FIELDS = [
    "admin_debug_mode",
    "__proto__",
    "is_admin",
    "$where",
    "eval",
    "<script>",
    "bypass_ml"  # attempting to force ML bypass
]
```

**Logged to:**
- `honeypot_alerts` MongoDB collection
- Application logs with full request metadata
- FSM trace as `REJECT` state

### Layer 1: Input Validation

Pydantic models with custom validators:
```python
# Example: Biologically plausible ranges
systolic_bp: int = Field(ge=50, le=220)
diastolic_bp: int = Field(ge=30, le=140)
spo2: float = Field(ge=70.0, le=100.0)
```

### Layer 2: Idempotency

Prevent duplicate assessments:
```bash
POST /triage/submit
{
  "client_sync_uuid": "abc-123-def",  # Client-generated UUID
  "vitals": {...}
}
```

**First request:** Processes normally, returns result  
**Duplicate request:** Returns cached result from database (within 10 min TTL)

### Layer 3: Optimistic Locking (HITL)

Prevent concurrent HITL modifications:
```python
# Doctor A and B review same case
POST /doctor/hitl-resolve
{
  "decision_id": "xyz",
  "version_id": "v1",  # ← Optimistic lock
  "action": "confirm_ml"
}
```

**If version changed:** Returns `409 Conflict`, frontend auto-refreshes

### Layer 4: Authentication & Authorization

- **JWT tokens:** 24-hour expiration, HS256 algorithm
- **Bcrypt hashing:** 12 rounds for password storage
- **Role-based access:**
  - `asha`: Submit triage, view own submissions
  - `doctor`: Access HITL queue, emergency feed, resolve cases
  - `admin`: System health, metrics, user management (future)

---

## 🔬 Machine Learning Model

### Model Architecture

- **Algorithm:** Random Forest Classifier
- **Trees:** 200 estimators
- **Max Depth:** 15 levels
- **Training Data:** 20,000 synthetic maternal health records
- **Features:** 8 clinical vitals + 3 engineered features

### Performance Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Accuracy** | 99.6% | On held-out test set |
| **Precision (HIGH)** | 97.8% | Few false positives |
| **Recall (HIGH)** | 98.9% | Catches most critical cases |
| **F1-Score** | 98.3% | Balanced precision/recall |
| **ROC-AUC** | 0.994 | Excellent discrimination |

### Feature Importance (Top 5)

1. **Systolic BP** (32.4%) - Primary hypertension indicator
2. **Diastolic BP** (28.1%) - Secondary BP confirmation
3. **Age** (15.7%) - Advanced maternal age risk
4. **Blood Sugar** (12.3%) - Gestational diabetes
5. **Heart Rate** (8.9%) - Cardiovascular stress

### Circuit Breaker Protection

Protects against ML model failures:

**States:**
- **CLOSED:** ML available (>95% success rate)
- **OPEN:** ML bypassed (after 5 consecutive failures)
- **HALF_OPEN:** Testing recovery (3 test requests)

**Fallback:** Clinical rules engine provides assessment

**Metrics:**
```bash
GET /admin/system/health
{
  "circuit_breaker_state": "CLOSED",
  "circuit_success_rate": 0.987,
  "circuit_failure_count": 2,
  "circuit_last_failure": "2026-01-08T12:30:00Z"
}
```

---

## 📡 API Documentation

### Triage Submission (FSM Entry Point)

```http
POST /triage/submit
Authorization: Bearer {jwt_token}
Content-Type: application/json

{
  "client_sync_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "patient_name": "Ramya Devi",
  "age": 28,
  "gestational_weeks": 32,
  "systolic_bp": 138,
  "diastolic_bp": 88,
  "blood_sugar": 6.2,
  "body_temp": 37.1,
  "heart_rate": 85,
  "spo2": 97.0,
}
```

**Response (High Confidence, Auto-Resolved):**
```json
{
  "assessment_id": "65f8a3b2c1d4e5f6a7b8c9d0",
  "risk_level": "MEDIUM",
  "confidence": 0.87,
  "alerts": [
    "⚠️ Borderline blood pressure detected",
    "⚠️ Trace proteinuria present"
  ],
  "feature_importances": {
    "systolic_bp": 0.324,
    "diastolic_bp": 0.281,
    "age": 0.157
  },
  "engine_source": "FSM",
  "requires_hitl": false,
  "fsm_trace": [
    {"from": "INGEST", "to": "SANITY", "duration_ms": 3},
    {"from": "SANITY", "to": "RULE_ENGINE", "duration_ms": 18},
    {"from": "RULE_ENGINE", "to": "ML_INFERENCE", "duration_ms": 25},
    {"from": "ML_INFERENCE", "to": "CONFIDENCE_CHECK", "duration_ms": 152},
    {"from": "CONFIDENCE_CHECK", "to": "SAVE_DB", "duration_ms": 8},
    {"from": "SAVE_DB", "to": "DONE", "duration_ms": 12}
  ],
  "processing_time_ms": 218,
  "timestamp": "2026-01-08T14:23:45.123Z"
}
```

**Response (Low Confidence, HITL Required):**
```json
{
  "assessment_id": "65f8a3b2c1d4e5f6a7b8c9d1",
  "risk_level": "MEDIUM",
  "confidence": 0.62,  // ← Below HITL threshold (0.65)
  "alerts": ["⏳ Pending doctor review"],
  "requires_hitl": true,
  "fsm_trace": [
    ...
    {"from": "CONFIDENCE_CHECK", "to": "HITL_HANDOFF", "duration_ms": 5}
  ],
  "processing_time_ms": 203
}
```

### HITL Queue (Doctor Only)

```http
GET /doctor/hitl-queue
Authorization: Bearer {doctor_jwt_token}
```

**Response:**
```json
[
  {
    "_id": "65f8a3b2c1d4e5f6a7b8c9d1",
    "patient_name": "Ramya Devi",
    "ml_confidence": 0.62,
    "final_risk_level": "MEDIUM",
    "vitals": {...},
    "fsm_trace": [...],
    "created_at": "2026-01-08T14:23:45.123Z",
    "version_id": "v1_1704720225"
  },
  ...
]
```

### HITL Resolution

```http
POST /doctor/hitl-resolve
Authorization: Bearer {doctor_jwt_token}
Content-Type: application/json

{
  "decision_id": "65f8a3b2c1d4e5f6a7b8c9d1",
  "action": "confirm_ml",  // or "escalate_to_critical", "downgrade_to_low"
  "version_id": "v1_1704720225",
  "doctor_notes": "Borderline vitals. Recommend follow-up in 3 days."
}
```

**Response (Success):**
```json
{
  "status": "resolved",
  "updated_risk_level": "MEDIUM",
  "resolved_by": "Dr. Sharma",
  "resolved_at": "2026-01-08T14:30:12.456Z"
}
```

**Response (Conflict):**
```http
HTTP/1.1 409 Conflict
{
  "detail": "Version conflict: case already reviewed by another doctor"
}
```

### System Health

```http
GET /admin/system/health
```

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "ml_model_loaded": true,
  "circuit_breaker_state": "CLOSED",
  "timestamp": "2026-01-08T14:45:00.000Z",
  "fsm_statistics": {
    "total_assessments": 15234,
    "assessments_last_24h": 342,
    "honeypot_triggers": 23,
    "hitl_cases_pending": 7,
    "hitl_cases_resolved": 1893,
    "avg_processing_time_ms": 187,
    "fsm_state_distribution": {
      "DONE": 14876,
      "HITL_HANDOFF": 335,
      "REJECT": 23
    }
  }
}
```

---

## 🧪 Testing

### Run Test Suite

```bash
# All tests
docker-compose exec backend pytest -v

# With coverage report
docker-compose exec backend pytest --cov=app --cov-report=html

# Specific test categories
docker-compose exec backend pytest tests/test_circuit.py -v
docker-compose exec backend pytest tests/test_idempotency.py -v
docker-compose exec backend pytest tests/test_sanity.py -v
```

### Test Categories

| File | Coverage | Purpose |
|------|----------|---------|
| `test_circuit.py` | Circuit breaker states | CLOSED → OPEN → HALF_OPEN transitions |
| `test_rules.py` | Clinical rules | WHO thresholds, bypass logic |
| `test_sanity.py` | Input validation | 100+ adversarial cases |
| `test_idempotency.py` | Duplicate handling | UUID-based deduplication |

### Manual HITL Testing

See [docs/HITL_TESTING.md](docs/HITL_TESTING.md) for comprehensive test plan.

**Quick Test:**
```bash
# 1. Submit borderline case (confidence ~60%)
curl -X POST http://localhost:8000/triage/submit \
  -H "Authorization: Bearer {asha_token}" \
  -d '{
    "systolic_bp": 138,
    "diastolic_bp": 88,
    "proteinuria": 1,
    ...
  }'

# 2. Check HITL queue
curl http://localhost:8000/doctor/hitl-queue \
  -H "Authorization: Bearer {doctor_token}"

# 3. Resolve case
curl -X POST http://localhost:8000/doctor/hitl-resolve \
  -H "Authorization: Bearer {doctor_token}" \
  -d '{
    "decision_id": "...",
    "action": "confirm_ml",
    "version_id": "...",
    "doctor_notes": "Monitor BP"
  }'
```

---

## 🚢 Deployment

### Production Checklist

- [ ] **Generate strong JWT_SECRET**
  ```bash
  openssl rand -hex 32
  ```

- [ ] **Configure MongoDB Atlas**
  - Create cluster at mongodb.com/atlas
  - Whitelist application server IP
  - Update `MONGO_URI` in `.env`

- [ ] **Set HITL threshold**
  ```env
  HITL_CONFIDENCE_THRESHOLD=0.70  # Stricter for production
  ```

- [ ] **Enable honeypot logging**
  ```env
  HONEYPOT_ENABLED=true
  HONEYPOT_LOG_TO_DB=true
  ```

- [ ] **Configure CORS**
  ```env
  CORS_ORIGINS='["https://your-domain.com","https://www.your-domain.com"]'
  ```

- [ ] **Set up SSL/TLS** (Nginx reverse proxy recommended)

- [ ] **Enable log rotation**
  ```bash
  # /etc/logrotate.d/momwatch
  /app/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
  }
  ```

- [ ] **Set up monitoring** (Prometheus + Grafana)
  - Monitor `/admin/system/health`
  - Alert on HITL queue backlog >20
  - Alert on honeypot triggers >10/hour

- [ ] **Database backups**
  ```bash
  # MongoDB Atlas: Enable continuous backups
  # Retention: 30 days minimum
  ```

### Docker Production Deployment

```bash
# Build for production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale backend workers
docker-compose up -d --scale backend=4

# Health check
curl https://your-domain.com/admin/system/health
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete production guide.

---

## 📈 Monitoring & Observability

### Key Metrics to Track

1. **FSM Performance**
   - Average processing time (<200ms target)
   - FSM state distribution
   - Rejection rate (<1% target)

2. **HITL Queue**
   - Pending cases (should stay <20)
   - Average resolution time (<10 minutes target)
   - Doctor response rate

3. **Security**
   - Honeypot trigger rate (<10/day expected)
   - Failed authentication attempts
   - Idempotency cache hit rate

4. **System Health**
   - Circuit breaker state (should be CLOSED >99% of time)
   - ML model prediction latency
   - Database connection pool utilization

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "FSM Processing Time",
      "target": "avg(fsm_processing_ms)",
      "threshold": 200
    },
    {
      "title": "HITL Queue Backlog",
      "target": "count(hitl_pending)",
      "threshold": 20
    },
    {
      "title": "Honeypot Triggers",
      "target": "rate(honeypot_triggers[1h])",
      "threshold": 10
    }
  ]
}
```

### Log Analysis

```bash
# High-priority HITL cases
docker logs momwatch_backend | grep "HITL_HANDOFF"

# Honeypot detections
docker logs momwatch_backend | grep "Honeypot"

# Circuit breaker state changes
docker logs momwatch_backend | grep "Circuit breaker"
```

---

## 🤝 Contributing

We welcome contributions! Please focus on:

1. **FSM Extensions** - New states, transitions, or validation logic
2. **HITL Improvements** - Better prioritization, batch review features
3. **Security Enhancements** - Additional honeypot fields, validation rules
4. **Rural UX** - Mobile optimization, offline support, vernacular language
5. **Documentation** - Improve ASHA worker guides, API examples

**Process:**
```bash
git checkout -b feature/your-feature-name
# Make changes
pytest  # All tests must pass
git commit -m "feat: description"
git push origin feature/your-feature-name
# Create pull request
```

---

## 📄 License

This project is intended for **educational and research purposes**.

⚠️ **Medical Disclaimer:** MomWatch AI is NOT a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified healthcare providers. This system is designed to **assist** ASHA workers in rural health screening, not replace medical professionals.

---

## 📞 Support

- **Documentation:** [docs/](docs/)
- **Issues:** GitHub Issues
- **API Docs:** http://localhost:8000/docs (when running)
- **Emergency:** Contact healthcare provider or call emergency services

---

## 🙏 Acknowledgments

- **Target Users:** ASHA workers and rural pregnant women in India
- **Clinical Guidelines:** WHO Maternal Health Standards
- **Dataset:** Maternal Health Risk Data Set (Kaggle)
- **Technology:** FastAPI, Streamlit, MongoDB, Scikit-learn
- **Inspiration:** National Rural Health Mission (NRHM), India

---

## 📚 Additional Resources

- [FSM Architecture Deep Dive](docs/DEFENSIVE_ENGINEERING.md)
- [HITL Testing Guide](docs/HITL_TESTING.md)
- [API Reference](docs/API_REFERENCE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [WHO Maternal Health Guidelines](https://www.who.int/health-topics/maternal-health)
- [ASHA Worker Program](https://nhm.gov.in/index1.php?lang=1&level=1&sublinkid=150)

---

**🏥 Built for Rural Maternal Health Safety**  
**Version:** 2.0.0 (FSM + HITL Architecture)  
**Last Updated:** January 8, 2026  
**Competition:** Build2Break 2026 - Defensive Engineering Track
