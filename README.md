# MomWatch AI - Maternal Health Monitoring System

![MomWatch AI](https://via.placeholder.com/800x200.png?text=MomWatch+AI+-+Making+Pregnancy+Safer)

## 🏥 Overview

**MomWatch AI** is a production-grade, AI-powered maternal health monitoring system designed to reduce pregnancy-related complications through early risk detection and clinical decision support. The system employs a defensively-engineered 3-layer risk assessment pipeline combining WHO clinical guidelines, machine learning, and advanced NLP AI.

### Key Features

- 🎯 **3-Layer Risk Assessment** - Validation → Clinical Rules → ML Model
- 🛡️ **Defensive Engineering** - Circuit breaker, idempotency, graceful degradation
- 🤖 **AI-Enhanced** - Zudu AI integration for advanced clinical insights
- 📊 **Explainable AI** - Feature importance visualization and clinical reasoning
- 🚨 **Real-time Alerts** - Automatic emergency flagging for healthcare providers
- 🔒 **HIPAA-Ready** - JWT authentication, encrypted communications
- 🐳 **Containerized** - Docker-based deployment with health checks

---

## 🚀 Quick Start

### Prerequisites

- **Docker** 24.0+ and **Docker Compose** 3.8+
- **4GB RAM** minimum (8GB recommended)
- **5GB free disk space**

### Installation

1. **Clone the repository:**
```bash
cd momwatch_ai
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

**Required Configuration:**
- Generate a secure `JWT_SECRET` (minimum 32 characters)
- Add your `ZUDU_API_KEY` (sign up at zudu.ai)
- MongoDB URI is pre-configured for Docker

3. **Start the application:**
```bash
docker-compose up --build
```

4. **Access the application:**
- **Frontend (Streamlit):** http://localhost:8501
- **Backend API Documentation:** http://localhost:8000/docs
- **MongoDB:** localhost:27017

### First-Time Setup

1. **Train the ML model:**
```bash
# Generate synthetic dataset
docker-compose exec backend python -m ml_ops.dataset_gen

# Train the model
docker-compose exec backend python -m ml_ops.train

# Evaluate performance
docker-compose exec backend python -m ml_ops.evaluate
```

2. **Create test accounts:**
   - Navigate to http://localhost:8501
   - Click "Register" and create a Mother account
   - Create a Doctor account for monitoring dashboard

---

## 📁 Project Structure

```
momwatch_ai/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # REST API endpoints
│   │   │   ├── auth.py        # Authentication (register/login)
│   │   │   ├── triage.py      # Main health assessment
│   │   │   ├── doctor.py      # Doctor dashboard APIs
│   │   │   ├── mother.py      # Mother profile APIs
│   │   │   └── admin.py       # System health monitoring
│   │   ├── engine/            # Risk assessment core
│   │   │   ├── sanity.py      # Layer 0: Input validation
│   │   │   ├── rules.py       # Layer 1: Clinical rules
│   │   │   ├── ml_model.py    # Layer 2: ML inference
│   │   │   ├── circuit.py     # Circuit breaker
│   │   │   ├── zudu_integration.py  # Zudu AI client
│   │   │   └── orchestrator.py      # Master coordinator
│   │   ├── db/                # Database layer
│   │   ├── models/            # Request/Response DTOs
│   │   └── utils/             # Shared utilities
│   ├── tests/                 # Comprehensive test suite
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                   # Streamlit frontend
│   ├── views/                 # Page components
│   │   ├── login.py
│   │   ├── mother_panel.py
│   │   ├── doctor_panel.py
│   │   ├── about.py
│   │   └── contact.py
│   ├── components/            # Reusable UI widgets
│   │   ├── vitals_form.py
│   │   ├── xai_chart.py
│   │   ├── health_passport.py
│   │   └── alert_card.py
│   ├── utils/                 # Frontend utilities
│   ├── app.py                 # Entry point
│   ├── Dockerfile
│   └── requirements.txt
│
├── ml_ops/                     # Machine learning pipeline
│   ├── dataset_gen.py         # Synthetic data generation
│   ├── train.py               # Model training
│   ├── evaluate.py            # Performance evaluation
│   └── model_store/           # Trained models
│
├── docs/                       # Documentation
│   ├── API_REFERENCE.md
│   ├── DEPLOYMENT.md
│   └── DEFENSIVE_ENGINEERING.md
│
├── docker-compose.yml          # Multi-container orchestration
├── .env.example               # Environment template
└── README.md
```

---

## 🏗️ Architecture

### System Components

```
┌─────────────────┐
│   Streamlit     │  User Interface (Mother/Doctor)
│    Frontend     │
└────────┬────────┘
         │ HTTP
         ↓
┌─────────────────┐
│   FastAPI       │  REST API with async support
│    Backend      │
└────────┬────────┘
         │
    ┌────┴────┐
    ↓         ↓
┌────────┐ ┌──────────────┐
│MongoDB │ │Risk Assessment│
│Database│ │   Engine      │
└────────┘ └───────┬───────┘
                   │
         ┌─────────┼─────────┐
         ↓         ↓         ↓
    ┌────────┐ ┌────────┐ ┌────────┐
    │Clinical│ │ML Model│ │Zudu AI │
    │ Rules  │ │        │ │        │
    └────────┘ └────────┘ └────────┘
```

### 3-Layer Risk Assessment Pipeline

**Layer 0: Adversarial Defense (Sanity Check)**
- Validates biologically plausible ranges
- Rejects negative values, reversed BP, extreme outliers
- Pydantic models with custom validators

**Layer 1: Clinical Rules Engine**
- WHO evidence-based thresholds
- Immediate CRITICAL flagging for:
  - Hypertensive crisis (BP ≥140/90)
  - Hypoxia (SpO2 <94%)
  - Severe tachycardia (HR >120)
  - Severe hypo/hyperglycemia
- Bypasses ML for critical cases (confidence: 100%)

**Layer 2: Machine Learning Model**
- Random Forest Classifier (200 trees)
- Trained on 20,000+ synthetic records
- Feature importance for explainability
- ~92% accuracy on test set

**Layer 3: AI Enhancement (Zudu AI)**
- Natural language clinical insights
- Recommended clinical actions
- Risk factor explanations
- Non-blocking integration (fallback on timeout)

### Circuit Breaker Pattern

Protects against cascading failures:

1. **CLOSED**: Normal operation, requests pass to ML
2. **OPEN**: ML bypassed after 5 failures, uses rules only
3. **HALF_OPEN**: Testing recovery after 60s timeout

---

## 🔐 Security Features

- **JWT Authentication** with 24-hour token expiration
- **Bcrypt Password Hashing** (12 rounds)
- **CORS Protection** with configurable origins
- **Input Validation** at API boundary
- **Role-Based Access Control** (Mother/Doctor)
- **Request Idempotency** prevents duplicate submissions
- **SQL Injection Protection** (NoSQL with schema validation)

---

## 📊 Clinical Thresholds

### CRITICAL Flags (Auto-escalation)
| Vital | Threshold | Risk |
|-------|-----------|------|
| Systolic BP | ≥140 mmHg | Preeclampsia |
| Diastolic BP | ≥90 mmHg | Preeclampsia |
| Blood Oxygen | <94% | Respiratory distress |
| Heart Rate | >120 bpm | Hemorrhage/Infection |
| Blood Sugar | <3.0 mmol/L | Seizure risk |
| Blood Sugar | >11.0 mmol/L | Gestational diabetes crisis |

### Additional Risk Factors
- **Age ≥35:** Advanced maternal age
- **Gestational weeks >40:** Post-term pregnancy
- **Temperature >38.5°C:** Infection risk

---

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
docker-compose exec backend pytest

# Run with coverage
docker-compose exec backend pytest --cov=app --cov-report=html

# Run specific test file
docker-compose exec backend pytest tests/test_sanity.py -v

# Run integration tests
docker-compose exec backend pytest tests/test_integration.py
```

### Test Coverage

- **Adversarial Defense:** 100+ edge cases
- **Clinical Rules:** All WHO thresholds
- **Circuit Breaker:** State transitions
- **Idempotency:** Duplicate handling
- **API Integration:** End-to-end flows

---

## 📈 Monitoring

### System Health Endpoint

```bash
curl http://localhost:8000/system/health
```

Returns:
```json
{
  "status": "healthy",
  "database": "connected",
  "circuit_breaker": "CLOSED",
  "ml_model": "loaded",
  "timestamp": "2026-01-08T10:30:00Z"
}
```

### Logs

- **Backend logs:** `./logs/momwatch.log`
- **Docker logs:** `docker-compose logs -f backend`

---

## 🛠️ Development

### Local Development (Without Docker)

1. **Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

2. **Frontend:**
```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

3. **MongoDB:**
```bash
docker run -d -p 27017:27017 mongo:6.0
```

### Environment Variables

See `.env.example` for complete configuration options.

**Critical Variables:**
- `JWT_SECRET`: Min 32 chars, cryptographically random
- `ZUDU_API_KEY`: From zudu.ai dashboard
- `MONGO_URI`: Connection string

---

## 🚢 Deployment

### Production Checklist

- [ ] Generate strong `JWT_SECRET` (openssl rand -hex 32)
- [ ] Configure production MongoDB with authentication
- [ ] Set up SSL/TLS certificates
- [ ] Enable MongoDB backups
- [ ] Configure log rotation
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Review and harden CORS settings
- [ ] Enable rate limiting
- [ ] Configure CDN for static assets
- [ ] Set up health check monitoring

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed production deployment guide.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

---

## 📄 License

This project is intended for **educational and research purposes**. 

⚠️ **Medical Disclaimer:** MomWatch AI is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified healthcare providers with any questions regarding a medical condition.

---

## 📞 Support

- **Documentation:** [docs/](docs/)
- **Issues:** GitHub Issues
- **Email:** support@momwatch.ai
- **Emergency:** Contact your healthcare provider or call 911

---

## 🙏 Acknowledgments

- **Dataset:** Maternal Health Risk Data Set (Kaggle)
- **AI Partner:** Zudu AI for advanced maternal health insights
- **Frameworks:** FastAPI, Streamlit, Scikit-learn
- **Community:** Open-source contributors

---

## 📚 Additional Resources

- [API Reference](docs/API_REFERENCE.md)
- [Defensive Engineering Guide](docs/DEFENSIVE_ENGINEERING.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [WHO Maternal Health Guidelines](https://www.who.int/health-topics/maternal-health)
- [CDC Pregnancy Information](https://www.cdc.gov/pregnancy)

---

**Built with ❤️ for maternal health safety**

Version: 1.0.0  
Last Updated: January 8, 2026
