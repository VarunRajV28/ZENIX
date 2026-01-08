# HITL Integration Test Case

## Objective
Verify that low-confidence triage assessments are correctly routed to HITL queue for doctor review.

## Prerequisites
- ✅ Backend running (port 8000)
- ✅ Frontend running (port 8501)
- ✅ ASHA account registered
- ✅ Doctor account registered

---

## Test Case 1: Trigger HITL with Borderline Vitals

### Input Data (Submit as ASHA)
```
Patient: Test HITL Case 1
Systolic BP: 138
Diastolic BP: 88
Heart Rate: 92
Blood Glucose: 128
Temperature: 99.1
Gestational Age: 34
Blood Oxygen: 94

Proteinuria: Trace
Edema: Mild
Vaginal Bleeding: No
Fetal Movement: Reduced
Previous Complications: Yes

Symptoms: "Mild headache, occasional dizziness, slight swelling"
```

### Expected Results
**Triage Response:**
- ✅ `requires_hitl: true`
- ✅ `fsm_trace` array present
- ✅ Last FSM state: `HITL_HANDOFF`
- ✅ `ml_confidence` < 0.65

**Backend Logs Should Show:**
```
FSM state transition: CONFIDENCE_CHECK → HITL_HANDOFF
Confidence 0.XX below threshold 0.65
```

---

## Test Case 2: Verify HITL Queue Display

### Steps (As Doctor)
1. Navigate to "HITL Queue" page
2. Verify case appears in pending list
3. Check case details show:
   - ✅ Patient name
   - ✅ ML risk level and confidence
   - ✅ Complete vitals
   - ✅ FSM trace timeline
   - ✅ Action buttons visible

---

## Test Case 3: Resolve HITL Case

### Action: Confirm ML Assessment
1. Click "✅ Confirm ML Assessment"
2. Verify success message
3. Check case removed from queue

### Expected Database State
```javascript
db.triage_decisions.findOne({patient_name: "Test HITL Case 1"})
// Should show:
{
  review_status: "REVIEWED",
  final_risk_level: "<ML_RISK_LEVEL>",
  doctor_notes: "Doctor confirmed ML assessment...",
  reviewed_by: "<doctor_user_id>",
  reviewed_at: ISODate(...)
}
```

---

## Test Case 4: High Confidence Bypass (Control)

### Input Data (Submit as ASHA)
```
Patient: Normal Case (No HITL)
Systolic BP: 120
Diastolic BP: 80
Heart Rate: 75
Blood Glucose: 95
Temperature: 98.6
Gestational Age: 28
Blood Oxygen: 98

Proteinuria: No
Edema: No
Vaginal Bleeding: No
Fetal Movement: Normal
Previous Complications: No

Symptoms: "Routine checkup, feeling fine"
```

### Expected Results
- ✅ `requires_hitl: false`
- ✅ Last FSM state: `DONE` (not HITL_HANDOFF)
- ✅ `ml_confidence` >= 0.65
- ✅ Case does NOT appear in HITL queue

---

## Test Case 5: Optimistic Locking (Concurrent Access)

### Setup
1. Open HITL queue in two browser tabs (two doctor sessions)
2. Both doctors view same pending case

### Steps
1. Doctor 1: Click "Confirm ML Assessment"
2. Doctor 2: Immediately click "Escalate"

### Expected Results
- ✅ Doctor 1: Success message
- ✅ Doctor 2: "Version Conflict" error
- ✅ Doctor 2's page auto-refreshes
- ✅ Case no longer in queue for Doctor 2

---

## Verification Commands

### Check HITL Queue Count
```powershell
docker exec momwatch_backend python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def check():
    uri = os.getenv('MONGO_URI')
    db_name = os.getenv('MONGO_DB_NAME')
    client = AsyncIOMotorClient(uri)
    db = client[db_name]
    
    pending = await db.triage_decisions.count_documents({'review_status': 'PENDING'})
    reviewed = await db.triage_decisions.count_documents({'review_status': 'REVIEWED'})
    
    print(f'Pending HITL cases: {pending}')
    print(f'Reviewed cases: {reviewed}')
    
    client.close()

asyncio.run(check())
"
```

### Check FSM Statistics
```bash
curl -X GET http://localhost:8000/admin/system/health \
  -H "Authorization: Bearer <TOKEN>"
```

Expected in response:
```json
{
  "fsm_stats": {
    "hitl_pending": 1,
    "hitl_resolved": 0,
    "state_distribution": {
      "HITL_HANDOFF": 1
    }
  }
}
```

---

## Success Criteria

✅ **All Pass:**
1. Borderline vitals trigger HITL (confidence < 65%)
2. Case appears in doctor's HITL queue
3. Doctor can view FSM trace
4. Doctor can resolve case (confirm/escalate/downgrade)
5. Resolved case disappears from queue
6. Normal vitals bypass HITL (confidence ≥ 65%)
7. Optimistic locking prevents concurrent resolution

---

## Troubleshooting

### Issue: No cases appearing in HITL queue
**Check:**
```powershell
docker logs momwatch_backend --tail 50 | Select-String "HITL"
```

### Issue: All cases bypassing HITL
**Verify threshold:**
```powershell
docker logs momwatch_backend | Select-String "HITL threshold"
# Should show: ✓ FSM: HITL threshold=0.65
```

### Issue: Frontend error "str object has no attribute 'get'"
**Fixed:** Backend now returns list directly (not wrapped in dict)

---

## Manual Database Inspection

```javascript
// Connect to MongoDB
use prescripto

// Find all HITL cases
db.triage_decisions.find({
  final_state: "HITL_HANDOFF",
  review_status: "PENDING"
}).pretty()

// Check FSM traces
db.triage_decisions.findOne({}, {fsm_trace: 1, _id: 0})
```
