# HITL Integration Testing Guide

## ✅ Completed Components

### Backend (FSM Architecture)
- ✅ FSM Orchestrator with 9 states
- ✅ FSM Repository (MongoDB operations)
- ✅ Honeypot Middleware (Layer 0 security)
- ✅ Triage API rewritten for FSM flow
- ✅ Doctor HITL endpoints (GET queue, POST resolve)
- ✅ Admin health endpoint with FSM statistics
- ✅ Configuration with HITL threshold (0.65)
- ✅ MongoDB indexes for triage_decisions collection

### Frontend (HITL Interface)
- ✅ HITL Queue view (`hitl_queue.py`)
- ✅ API client methods (`get_hitl_queue`, `resolve_hitl`)
- ✅ Navigation integration (Doctor sidebar)
- ✅ UI for reviewing cases with FSM trace
- ✅ Action buttons (Confirm, Escalate, Downgrade)
- ✅ Optimistic locking with version conflict handling

---

## 🧪 Testing Checklist

### Test 1: Normal High-Confidence Flow (Bypass HITL)
**Scenario:** Submit vitals that produce confidence ≥65%

**Steps:**
1. Login as ASHA worker
2. Submit triage assessment with normal vitals:
   ```
   Systolic BP: 120
   Diastolic BP: 80
   Heart Rate: 75
   Temperature: 98.6
   Blood Glucose: 95
   Gestational Age: 28
   
   ```

**Expected:**
- FSM trace shows: INGEST → SANITY → RULE_ENGINE → ML_INFERENCE → CONFIDENCE_CHECK → SAVE_DB → DONE
- Response includes `requires_hitl: false`
- Case does NOT appear in HITL queue
- Risk level assigned automatically

---

### Test 2: Low-Confidence Trigger HITL
**Scenario:** Submit vitals that produce confidence <65%

**Steps:**
1. Login as ASHA worker
2. Submit triage with borderline vitals:
   ```
   Systolic BP: 138
   Diastolic BP: 88
   Heart Rate: 92
   Temperature: 99.2
   Blood Glucose: 130
   Gestational Age: 34
   
   ```

**Expected:**
- FSM trace shows: INGEST → SANITY → RULE_ENGINE → ML_INFERENCE → CONFIDENCE_CHECK → HITL_HANDOFF
- Response includes `requires_hitl: true`, `fsm_trace` array
- Case appears in doctor HITL queue with PENDING status

---

### Test 3: Doctor HITL Queue Review
**Scenario:** Doctor reviews and resolves low-confidence case

**Steps:**
1. Login as Doctor
2. Navigate to "HITL Queue" from sidebar
3. Verify pending case appears with:
   - Patient name
   - ML risk level
   - Confidence score (<65%)
   - FSM trace showing HITL_HANDOFF
   - Full vitals display
4. Click "✅ Confirm ML Assessment"

**Expected:**
- Success message displayed
- Case removed from HITL queue
- Decision saved with review_status: REVIEWED
- Final risk level matches ML assessment

---

### Test 4: Doctor Escalation
**Scenario:** Doctor overrides ML and escalates risk

**Steps:**
1. Find case with ML risk = MEDIUM in HITL queue
2. Review vitals and clinical context
3. Click "⬆️ Escalate to Higher Risk"

**Expected:**
- Final risk level becomes HIGH (one tier up)
- Doctor notes: "Doctor escalated from MEDIUM to HIGH"
- Review status: REVIEWED
- Case removed from queue

---

### Test 5: Doctor Downgrade
**Scenario:** Doctor overrides ML and downgrades risk

**Steps:**
1. Find case with ML risk = HIGH in HITL queue
2. Review vitals and determine ML overestimated
3. Click "⬇️ Downgrade to Lower Risk"

**Expected:**
- Final risk level becomes MEDIUM (one tier down)
- Doctor notes: "Doctor downgraded from HIGH to MEDIUM"
- Review status: REVIEWED
- Case removed from queue

---

### Test 6: Optimistic Locking (Version Conflict)
**Scenario:** Two doctors try to resolve same case simultaneously

**Steps:**
1. Open HITL queue in two browser tabs (two doctor sessions)
2. Both doctors select same pending case
3. Doctor 1 clicks "Confirm ML Assessment"
4. Doctor 2 immediately clicks "Escalate"

**Expected:**
- Doctor 1: Success, case resolved
- Doctor 2: Error "Version Conflict: Case already reviewed by another doctor"
- Page auto-refreshes for Doctor 2
- Case no longer in queue

---

### Test 7: Idempotency Check
**Scenario:** Resubmit same assessment with identical client_sync_uuid

**Steps:**
1. Submit triage with low confidence
2. Note the `client_sync_uuid` from response
3. Submit EXACT same vitals again (frontend should reuse UUID if patient unchanged)

**Expected:**
- Backend returns cached result immediately
- FSM trace shows idempotency hit
- No duplicate entry in triage_decisions collection
- Same decision_id returned

---

### Test 8: Honeypot Detection
**Scenario:** Malicious request with honeypot field

**Steps:**
1. Use API client (Postman/curl) to POST /triage with:
   ```json
   {
     "vitals": {
       "systolic_bp": 120,
       "admin_debug_mode": true,  // HONEYPOT FIELD
       ...
     }
   }
   ```

**Expected:**
- Request rejected with 400 Bad Request
- Error message: "Malicious field detected: admin_debug_mode"
- Alert logged to honeypot_alerts collection
- FSM never executes

---

### Test 9: FSM Statistics in Admin Health
**Scenario:** Check FSM metrics in system health endpoint

**Steps:**
1. Login as Doctor
2. Navigate to system health (if exposed in UI, or use API directly)
3. Check `/admin/system/health` response

**Expected Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "ml_model": "loaded",
  "fsm_stats": {
    "total_decisions": 15,
    "hitl_pending": 3,
    "hitl_resolved": 5,
    "avg_confidence": 0.72,
    "state_distribution": {
      "DONE": 10,
      "HITL_HANDOFF": 3,
      "REJECT": 2
    }
  },
  "honeypot": {
    "enabled": true,
    "alerts_today": 1
  }
}
```

---

### Test 10: FSM Timeout Handling
**Scenario:** Simulate FSM timeout (if ML inference takes >30s)

**Steps:**
1. Temporarily modify `FSM_STATE_TIMEOUT_SECONDS` to 1 in config
2. Submit triage assessment
3. Observe behavior

**Expected:**
- FSM should handle timeout gracefully
- Log warning: "FSM timeout in state ML_INFERENCE"
- Fallback to HITL_HANDOFF or REJECT state
- User receives error message

---

## 🔍 Monitoring Commands

### Check Backend Logs
```powershell
docker logs momwatch_backend --tail 100 -f
```

### Check Frontend Logs
```powershell
docker logs momwatch_frontend --tail 50 -f
```

### Query MongoDB Collections
```bash
docker exec -it momwatch_mongodb mongosh momwatch_db
```

```javascript
// Check triage decisions
db.triage_decisions.find().limit(5)

// Check HITL pending cases
db.triage_decisions.find({review_status: "PENDING"})

// Check honeypot alerts
db.honeypot_alerts.find().sort({timestamp: -1}).limit(10)

// FSM statistics
db.triage_decisions.aggregate([
  {$group: {
    _id: "$final_state",
    count: {$sum: 1}
  }}
])
```

---

## 🎯 Success Criteria

- [ ] High-confidence assessments bypass HITL (Test 1)
- [ ] Low-confidence assessments trigger HITL (Test 2)
- [ ] HITL queue displays pending cases correctly (Test 3)
- [ ] Doctor can confirm ML assessment (Test 3)
- [ ] Doctor can escalate risk (Test 4)
- [ ] Doctor can downgrade risk (Test 5)
- [ ] Optimistic locking prevents race conditions (Test 6)
- [ ] Idempotency prevents duplicate processing (Test 7)
- [ ] Honeypot catches malicious fields (Test 8)
- [ ] FSM statistics available in health endpoint (Test 9)
- [ ] No unhandled exceptions in logs
- [ ] Frontend HITL UI renders correctly
- [ ] All FSM traces captured in database

---

## 🐛 Known Issues to Watch

1. **Version Conflict Message:** Should auto-refresh page
2. **Confidence Edge Cases:** Exactly 0.65 should NOT trigger HITL (>= threshold)
3. **MongoDB Connection:** Ensure indexes created on startup
4. **ML Model Loading:** Check logs for "ML model loaded" confirmation

---

## 📊 Next Steps After Testing

1. **Docker Hardening** (docker-compose.yml)
   - Add CPU/memory limits
   - Configure logging with rotation
   - Enable read-only filesystems
   - Network isolation

2. **Frontend Enhancements**
   - Add HITL statistics dashboard
   - Export HITL review history
   - Bulk actions for multiple cases

3. **Documentation**
   - Update API_REFERENCE.md with HITL endpoints
   - Add FSM architecture diagram
   - Create deployment guide for Build2Break

---

## 🚀 Quick Smoke Test

Run this sequence to verify basic functionality:

```bash
# 1. Check all containers healthy
docker-compose ps

# 2. Verify FSM initialization
docker logs momwatch_backend | grep "FSM"

# 3. Access frontend
http://localhost:8501

# 4. Login as ASHA → Submit borderline case → Check HITL queue as Doctor
```

Expected: Full flow works end-to-end with FSM trace visible.
