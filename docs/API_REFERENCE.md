# API Reference - MomWatch AI

Complete REST API documentation for the MomWatch AI backend.

**Base URL:** `http://localhost:8000`  
**API Documentation:** http://localhost:8000/docs (Swagger UI)

---

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### POST /auth/register

Create a new user account.

**Request Body:**
```json
{
  "email": "string",
  "password": "string",
  "full_name": "string",
  "role": "mother" | "doctor",
  "age": 28,  // Required for mother
  "gestational_weeks": 20  // Required for mother
}
```

**Response (201):**
```json
{
  "user_id": "string",
  "email": "string",
  "full_name": "string",
  "role": "mother",
  "message": "Account created successfully"
}
```

**Error Codes:**
- `400`: Email already registered
- `422`: Validation error

---

### POST /auth/login

Authenticate and receive JWT token.

**Request Body (Form Data):**
```
username=email@example.com
password=your_password
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJ...",
  "token_type": "bearer",
  "user": {
    "user_id": "string",
    "email": "string",
    "full_name": "string",
    "role": "mother"
  }
}
```

**Error Codes:**
- `401`: Invalid credentials

---

## Triage Assessment

### POST /triage

Submit health vitals for risk assessment. **Idempotent.**

**Headers:**
```
Authorization: Bearer <token>
x-idempotency-key: <uuid>  // Required for idempotency
```

**Request Body:**
```json
{
  "age": 28,
  "systolic_bp": 120,
  "diastolic_bp": 80,
  "blood_sugar": 5.0,
  "body_temperature": 37.0,
  "heart_rate": 75,
  "blood_oxygen": 98,
  "gestational_weeks": 20
}
```

**Response (200):**
```json
{
  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "confidence": 0.95,
  "alerts": ["HYPERTENSIVE_CRISIS"],
  "clinical_notes": [
    "Blood pressure 145/95 exceeds preeclampsia threshold",
    "Immediate medical evaluation recommended"
  ],
  "feature_importances": {
    "systolic_bp": 0.35,
    "age": 0.18,
    "blood_sugar": 0.12,
    "heart_rate": 0.10
  },
  "engine_source": "CLINICAL_RULES" | "ML_MODEL" | "HYBRID",
  "fallback_active": false,
  "zudu_insights": {
    "clinical_insights": "Patient shows signs of gestational hypertension...",
    "recommended_actions": [
      "Monitor BP every 4 hours",
      "Consider magnesium sulfate prophylaxis"
    ],
    "urgency_score": 8.5
  },
  "timestamp": "2026-01-08T10:30:00Z",
  "processing_time_ms": 342
}
```

**Response Headers:**
- `X-Idempotent-Replay: true` (if cached response returned)

**Error Codes:**
- `422`: Validation error (invalid vitals)
- `401`: Unauthorized

**Validation Rules:**
- Age: 15-60 years
- Systolic BP: 70-230 mmHg (must be > diastolic)
- Diastolic BP: 40-140 mmHg
- Heart Rate: 45-180 bpm
- Body Temperature: 34-42°C
- Blood Oxygen: 70-100%
- Blood Sugar: 0.5-30 mmol/L
- Gestational Weeks: 1-42

---

## Doctor Endpoints

### GET /dashboard/emergency

Fetch CRITICAL patients from last 24 hours. **Doctor only.**

**Headers:**
```
Authorization: Bearer <token>
```

**Response (200):**
```json
[
  {
    "patient_id": "user-uuid-123",
    "age": 35,
    "gestational_weeks": 28,
    "timestamp": "2026-01-08T09:15:00Z",
    "vitals": {
      "systolic_bp": 155,
      "diastolic_bp": 95,
      "heart_rate": 125,
      "blood_oxygen": 92
    },
    "risk_level": "CRITICAL",
    "alerts": ["HYPERTENSIVE_CRISIS", "TACHYCARDIA", "HYPOXIA"],
    "clinical_notes": [...]
  }
]
```

**Error Codes:**
- `403`: Doctor access required
- `401`: Unauthorized

---

### GET /patients/priority

Get priority-sorted patient list. **Doctor only.**

**Response (200):**
```json
[
  {
    "patient_id": "string",
    "priority_score": 8.5,
    "risk_level": "CRITICAL",
    "age": 35,
    "gestational_weeks": 28,
    "last_checkup": "2026-01-08T08:00:00Z",
    "alerts": ["HYPERTENSIVE_CRISIS"]
  }
]
```

**Priority Score Calculation:**
```
Priority = (ML_Risk_Level × 0.7) + (Hours_Since_Last_Checkup × 0.3)
```

---

### GET /patients/{patient_id}/details

Get detailed patient history. **Doctor only.**

**Response (200):**
```json
{
  "patient_id": "string",
  "age": 28,
  "gestational_weeks": 20,
  "current_risk_level": "MEDIUM",
  "total_assessments": 15,
  "critical_count": 2,
  "history": [
    {
      "timestamp": "2026-01-08T10:00:00Z",
      "risk_level": "MEDIUM",
      "confidence": 0.87,
      "vitals": {...},
      "alerts": [],
      "engine_source": "ML_MODEL"
    }
  ]
}
```

---

## Mother Endpoints

### GET /profile

Get mother's profile. **Mother only.**

**Response (200):**
```json
{
  "user_id": "string",
  "email": "string",
  "full_name": "string",
  "age": 28,
  "gestational_weeks": 20,
  "pre_existing_conditions": "Type 1 diabetes",
  "created_at": "2026-01-01T00:00:00Z"
}
```

---

### PUT /profile

Update mother's profile. **Mother only.**

**Request Body:**
```json
{
  "full_name": "string",
  "age": 28,
  "gestational_weeks": 21,
  "pre_existing_conditions": "string"
}
```

**Response (200):**
```json
{
  "message": "Profile updated successfully",
  "updated_fields": ["age", "gestational_weeks"]
}
```

---

### GET /history

Get triage assessment history. **Mother only.**

**Response (200):**
```json
[
  {
    "timestamp": "2026-01-08T10:00:00Z",
    "risk_level": "LOW",
    "confidence": 0.92,
    "vitals": {...},
    "alerts": [],
    "engine_source": "ML_MODEL"
  }
]
```

---

### GET /health-passport

Generate comprehensive health report. **Mother only.**

**Response (200):**
```json
{
  "profile": {...},
  "summary_statistics": {
    "total_assessments": 30,
    "low_risk_count": 20,
    "medium_risk_count": 8,
    "high_risk_count": 2,
    "critical_count": 0
  },
  "history": [...],
  "generated_at": "2026-01-08T10:30:00Z"
}
```

---

## Admin Endpoints

### GET /system/health

Get system health status.

**Response (200):**
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "latency_ms": 15
  },
  "circuit_breaker": {
    "state": "CLOSED",
    "failure_count": 0
  },
  "ml_model": {
    "loaded": true,
    "version": "RandomForest_v1.0.0"
  },
  "timestamp": "2026-01-08T10:30:00Z"
}
```

---

### GET /metrics

Get system metrics and performance data.

**Response (200):**
```json
{
  "total_requests": 1523,
  "total_users": 87,
  "active_sessions": 12,
  "avg_response_time_ms": 245,
  "circuit_breaker_trips": 3,
  "cache_hit_rate": 0.67
}
```

---

## Error Responses

### Standard Error Format

```json
{
  "detail": "Error message",
  "error_type": "VALIDATION_ERROR",
  "field": "systolic_bp",
  "timestamp": "2026-01-08T10:30:00Z"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

## Rate Limiting

- **Anonymous:** 100 requests/hour
- **Authenticated:** 1000 requests/hour
- **Triage endpoint:** 60 requests/hour per user

Rate limit headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1704711000
```

---

## Idempotency

The `/triage` endpoint supports idempotency to prevent duplicate submissions.

**How it works:**
1. Generate a UUID v4 idempotency key
2. Include in `x-idempotency-key` header
3. If same key used within 10 minutes, cached response returned
4. Response includes `X-Idempotent-Replay: true` header

**Example:**
```bash
curl -X POST http://localhost:8000/triage \
  -H "Authorization: Bearer <token>" \
  -H "x-idempotency-key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{...vitals...}'
```

---

## Webhooks (Future Feature)

Coming soon: Real-time notifications for critical events.

---

For interactive API documentation, visit:
**http://localhost:8000/docs** (Swagger UI)  
**http://localhost:8000/redoc** (ReDoc)
