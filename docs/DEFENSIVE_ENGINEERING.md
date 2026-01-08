# Defensive Engineering - MomWatch AI

This document outlines all defensive engineering patterns, attack scenarios, and failure mode handling implemented in MomWatch AI.

---

## Table of Contents

1. [Overview](#overview)
2. [3-Layer Defense Architecture](#3-layer-defense-architecture)
3. [Attack Scenarios & Mitigations](#attack-scenarios--mitigations)
4. [Failure Modes & Recovery](#failure-modes--recovery)
5. [Circuit Breaker Pattern](#circuit-breaker-pattern)
6. [Idempotency Mechanism](#idempotency-mechanism)
7. [Data Validation Strategy](#data-validation-strategy)
8. [Security Hardening](#security-hardening)

---

## Overview

MomWatch AI is engineered with **defense in depth** - multiple layers of protection ensuring the system remains operational and accurate even under adversarial conditions or component failures.

### Core Principles

1. **Fail-Fast Validation** - Reject invalid inputs at API boundary
2. **Graceful Degradation** - System works even if ML model fails
3. **Zero Silent Failures** - All errors logged and surfaced appropriately
4. **Audit Everything** - Complete trail of all decisions
5. **Idempotent Operations** - Duplicate requests safely handled

---

## 3-Layer Defense Architecture

```
Request → [Layer 0: Sanity] → [Layer 1: Rules] → [Layer 2: ML] → Response
          ↓ Reject           ↓ BYPASS if       ↓ Fallback
          Invalid            CRITICAL          to Layer 1
```

### Layer 0: Adversarial Defense (Sanity Check)

**Purpose:** Reject biologically impossible inputs before they reach database or ML model

**Implementation:** `app/engine/sanity.py`

**Validation Rules:**

| Field | Min | Max | Additional Rules |
|-------|-----|-----|-----------------|
| age | 15 | 60 | Reproductive age range |
| systolic_bp | 70 | 230 | Must be > diastolic_bp |
| diastolic_bp | 40 | 140 | Must be < systolic_bp |
| heart_rate | 45 | 180 | - |
| body_temperature | 34 | 42 | Flag hypothermia (<35°C), hyperthermia (>40°C) |
| blood_oxygen | 70 | 100 | Percentage value |
| blood_sugar | 0.5 | 30 | mmol/L |
| gestational_weeks | 1 | 42 | Full pregnancy range |

**Custom Validators:**

```python
@root_validator
def check_blood_pressure_consistency(cls, values):
    """Ensure systolic > diastolic (biological constraint)"""
    if values['systolic_bp'] <= values['diastolic_bp']:
        raise ValueError(
            "systolic_bp must be greater than diastolic_bp - "
            "biological constraint violation"
        )
    return values
```

---

### Layer 1: Clinical Rules Engine

**Purpose:** Implement WHO evidence-based thresholds that bypass ML for critical cases

**Implementation:** `app/engine/rules.py`

**CRITICAL Thresholds (bypass_ml=True):**

1. **Hypertensive Crisis:** SBP ≥140 OR DBP ≥90
   - Risk: Preeclampsia
   - Action: Immediate medical evaluation

2. **Hypoxia:** SpO2 <94%
   - Risk: Respiratory distress
   - Action: Oxygen therapy, assess respiratory function

3. **Severe Tachycardia:** HR >120 bpm
   - Risk: Hemorrhage, infection, cardiac issues
   - Action: Vital sign monitoring, investigate cause

4. **Severe Hypoglycemia:** Blood sugar <3.0 mmol/L
   - Risk: Seizures, loss of consciousness
   - Action: Immediate glucose administration

5. **Severe Hyperglycemia:** Blood sugar >11.0 mmol/L
   - Risk: Gestational diabetes crisis, DKA
   - Action: Insulin therapy, monitor ketones

**Why Bypass ML?**
- Medical emergencies require 100% confidence
- No margin for ML error in life-threatening situations
- Clinical guidelines are deterministic and proven

---

### Layer 2: Machine Learning Model

**Purpose:** Nuanced risk assessment for non-critical cases

**Implementation:** `app/engine/ml_model.py`

**Model Details:**
- Algorithm: Random Forest Classifier (200 trees)
- Features: 8 vitals + 3 engineered features
- Training: 20,000 synthetic maternal health records
- Accuracy: ~92% on test set

**Feature Engineering:**
```python
BP_Ratio = Systolic / Diastolic  # Cardiovascular stress indicator
Age_Risk_Score = 1 if age >= 35 else 0  # Advanced maternal age
Gestational_Risk = 1 if weeks > 40 or weeks < 12 else 0  # High-risk periods
```

**Explainability:**
- Feature importance scores returned with every prediction
- Clinical significance mapped to each feature
- Transparency for healthcare providers

---

## Attack Scenarios & Mitigations

### 1. Adversarial Input Attacks

**Scenario:** Attacker sends malicious inputs to crash system or manipulate results

#### Attack 1.1: Negative Values
```json
{"age": -5, "systolic_bp": -120, "heart_rate": -75}
```

**Mitigation:**
- Pydantic validators enforce `ge=minimum_value`
- Returns 422 with clear error message
- Never reaches database or ML model

**Test:** `test_sanity.py::test_negative_age`

---

#### Attack 1.2: Reversed Blood Pressure
```json
{"systolic_bp": 80, "diastolic_bp": 120}
```

**Mitigation:**
- `@root_validator` checks `systolic > diastolic`
- Rejects with biological constraint explanation
- Prevents nonsensical data in system

**Test:** `test_sanity.py::test_reversed_blood_pressure`

---

#### Attack 1.3: Extreme Outliers
```json
{"heart_rate": 500, "blood_oxygen": 200, "systolic_bp": 999}
```

**Mitigation:**
- Field validators enforce biological maximums
- Prevents integer overflow/underflow
- Protects ML model from training data poisoning

**Test:** `test_sanity.py::test_extreme_outlier_heart_rate`

---

#### Attack 1.4: Type Confusion
```json
{"age": "DROP TABLE users;--", "systolic_bp": "NaN"}
```

**Mitigation:**
- Pydantic enforces strict typing (int, float)
- SQL injection irrelevant (NoSQL with schema)
- Type coercion failures return 422

**Test:** `test_sanity.py::test_type_validation`

---

#### Attack 1.5: Null Injection
```json
{"age": null, "systolic_bp": 120, ...}
```

**Mitigation:**
- All required fields enforce `...` (Pydantic required)
- No null values allowed in vitals
- Clear error: "field required"

**Test:** Integration tests

---

### 2. Denial of Service (DoS)

#### Attack 2.1: Request Flooding
**Scenario:** 10,000 requests/second to overload system

**Mitigations:**
1. **Rate Limiting:** 1000 requests/hour per authenticated user
2. **Connection Pooling:** MongoDB max pool size limits concurrent connections
3. **Async Processing:** Non-blocking I/O handles high concurrency
4. **Idempotency:** Duplicate requests return cached results instantly
5. **Circuit Breaker:** Prevents cascade failures under load

---

#### Attack 2.2: Slowloris Attack
**Scenario:** Slow requests to exhaust server resources

**Mitigations:**
1. **Request Timeout:** 30-second timeout on triage endpoint
2. **Connection Timeout:** Uvicorn worker timeout
3. **Health Checks:** Docker restarts unhealthy containers

---

### 3. Database Failures

#### Scenario 3.1: MongoDB Connection Lost

**Detection:**
- Health check fails: `db.admin.command('ping')`
- Connection pool exhausted

**Mitigations:**
1. **Retry Logic:** Exponential backoff (3 attempts)
2. **Connection Pooling:** Auto-reconnect on pool refresh
3. **Graceful Degradation:** Return cached results if available
4. **Health Endpoint:** Surfaces DB status to monitoring

**Recovery:**
- Docker health check restarts container
- MongoDB persistent volumes prevent data loss

**Code:**
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2))
async def connect_db():
    client = AsyncIOMotorClient(MONGO_URI)
    await client.admin.command('ping')
    return client
```

---

#### Scenario 3.2: Database Corruption

**Prevention:**
- Schema validation on all writes
- Pydantic models enforce data integrity
- MongoDB ACID transactions for critical operations

**Recovery:**
- Daily backups (Docker volume snapshots)
- Point-in-time recovery capability

---

### 4. ML Model Failures

#### Scenario 4.1: Model File Missing/Corrupted

**Detection:**
```python
try:
    model = joblib.load(MODEL_PATH)
except Exception as e:
    logger.critical(f"ML model load failed: {e}")
```

**Mitigation:**
- Circuit breaker opens immediately
- System falls back to Layer 1 (Clinical Rules)
- Health endpoint reports `ml_model.loaded: false`
- Admin alerted to retrain/restore model

**User Impact:** Zero - seamless fallback to rules

---

#### Scenario 4.2: Model Returns Invalid Predictions

**Detection:**
- Predictions outside [0, 1] probability range
- NaN or infinity in feature importances

**Mitigation:**
```python
if not (0 <= confidence <= 1):
    raise MLModelException("Invalid confidence score")
    # Triggers circuit breaker
```

**Fallback:** Layer 1 clinical rules

---

#### Scenario 4.3: Model Inference Timeout

**Timeout:** 5 seconds for ML prediction

**Mitigation:**
```python
async with asyncio.timeout(5):
    prediction = await ml_model.predict(vitals)
```

**On Timeout:**
- Circuit breaker opens
- Fallback to clinical rules
- User receives result (no delay)

---

### 5. Zudu AI API Failures

#### Scenario 5.1: Zudu API Down

**Detection:**
- HTTP connection timeout (10 seconds)
- 5xx server errors

**Mitigation:**
- **Non-Blocking:** Zudu call runs asynchronously
- **Timeout:** 10-second max wait
- **Fallback:** System proceeds without Zudu insights
- **Retry Logic:** 3 attempts with exponential backoff

**User Impact:** Minimal - base assessment still provided

**Code:**
```python
try:
    zudu_insights = await zudu_client.analyze(vitals, timeout=10)
except (TimeoutError, ConnectionError):
    logger.warning("Zudu AI unavailable, proceeding without insights")
    zudu_insights = {"clinical_insights": "AI unavailable"}
```

---

#### Scenario 5.2: Zudu API Rate Limited

**Detection:** HTTP 429 Too Many Requests

**Mitigation:**
- Respect `Retry-After` header
- Exponential backoff
- Graceful degradation

---

## Circuit Breaker Pattern

### State Machine

```
    [CLOSED] ──5 failures──> [OPEN]
       ↑                        │
       │                    60s timeout
       │                        │
       └──3 successes──  [HALF_OPEN]
                              │
                         1 failure
                              │
                              ↓
                          [OPEN]
```

### Implementation

**File:** `app/engine/circuit.py`

**Configuration:**
```python
FAILURE_THRESHOLD = 5        # Open after 5 failures
TIMEOUT_SECONDS = 60         # Test recovery after 60s
HALF_OPEN_ATTEMPTS = 3       # Require 3 successes to close
```

**State Behaviors:**

| State | Behavior | Transition |
|-------|----------|------------|
| CLOSED | All requests pass to ML | 5 failures → OPEN |
| OPEN | All requests bypass ML | 60s → HALF_OPEN |
| HALF_OPEN | Test requests pass to ML | 3 successes → CLOSED, 1 failure → OPEN |

**Monitoring:**
```bash
curl http://localhost:8000/system/health | jq .circuit_breaker
{
  "state": "CLOSED",
  "failure_count": 0,
  "last_failure_time": null
}
```

---

## Idempotency Mechanism

### Purpose
Prevent duplicate triage submissions (e.g., double-click, network retry)

### Implementation

**TTL:** 10 minutes

**Workflow:**
1. Client generates UUID v4 idempotency key
2. Include in `x-idempotency-key` header
3. Backend checks MongoDB `idempotency_keys` collection
4. If key exists (< 10 min old): Return cached response
5. If key new: Process request, cache result

**Database Schema:**
```python
{
    "idempotency_key": str,  # UUID, unique index
    "user_id": str,
    "request_hash": str,     # SHA256 of request body
    "response_data": dict,
    "created_at": datetime   # TTL index (600 seconds)
}
```

**Benefits:**
- Prevents duplicate assessments
- Reduces database writes
- Faster response for retries (cache hit)

**Test:** `test_idempotency.py`

---

## Data Validation Strategy

### Multi-Layer Validation

1. **Type Validation** (Pydantic): Ensures correct data types
2. **Range Validation** (Pydantic): Biological constraints
3. **Business Logic Validation** (Custom): Systolic > diastolic
4. **Schema Validation** (MongoDB): Database-level enforcement

### Error Reporting

**User-Friendly Errors:**
```json
{
  "detail": [
    {
      "loc": ["body", "systolic_bp"],
      "msg": "ensure this value is greater than 70",
      "type": "value_error.number.not_gt",
      "biological_constraint": "Systolic BP must be 70-230 mmHg"
    }
  ]
}
```

---

## Security Hardening

### Authentication
- JWT tokens with 24-hour expiration
- Bcrypt password hashing (12 rounds)
- No plaintext passwords ever stored

### Authorization
- Role-based access control (Mother/Doctor)
- Endpoint protection via `get_current_user` dependency
- Doctor-only endpoints return 403 for mothers

### Input Sanitization
- Pydantic strict mode prevents injection
- NoSQL with schema validation (no SQL injection)
- Email validation regex

### CORS
- Configurable allowed origins
- Credentials support disabled by default
- Preflight caching

### Logging
- Sensitive data (passwords) never logged
- JWT tokens redacted in logs
- Audit trail for all critical operations

---

## Failure Recovery Procedures

### ML Model Failure
1. Circuit breaker opens
2. System uses clinical rules
3. Alert admin via health endpoint
4. Retrain model: `docker-compose exec backend python -m ml_ops.train`
5. Circuit automatically tests recovery

### Database Failure
1. Retry logic attempts reconnection
2. If persistent: Docker health check restarts container
3. Restore from backup if needed
4. Verify data integrity

### Complete System Failure
1. Docker Compose restarts all containers
2. Health checks validate each service
3. Rolling restart to minimize downtime
4. Check logs: `docker-compose logs -f`

---

## Monitoring & Alerting

### Health Checks

**Backend:**
```bash
docker inspect momwatch_backend --format='{{.State.Health.Status}}'
```

**Database:**
```bash
docker inspect momwatch_mongodb --format='{{.State.Health.Status}}'
```

### Metrics to Monitor

1. **Circuit Breaker State** - Alert if OPEN > 5 minutes
2. **Database Connection** - Alert if unhealthy
3. **ML Model Load Status** - Alert if failed to load
4. **API Response Times** - Alert if p95 > 1000ms
5. **Error Rate** - Alert if > 5%

---

## Testing Strategy

### Unit Tests
- Every validation rule
- All attack scenarios
- Circuit breaker state transitions

### Integration Tests
- End-to-end API flows
- Database operations
- Authentication flows

### Chaos Engineering
- Kill MongoDB during request
- Corrupt ML model file
- Simulate Zudu API timeout
- Network partition testing

**Run Tests:**
```bash
docker-compose exec backend pytest tests/ -v --cov=app
```

---

## Conclusion

MomWatch AI is engineered to **never fail silently**. Every component has:
- Fallback mechanism
- Comprehensive logging
- Clear error messages
- Graceful degradation path

The result: A life-critical healthcare system that remains operational and accurate even under adversarial conditions.

---

**Last Updated:** January 8, 2026  
**Version:** 1.0.0
