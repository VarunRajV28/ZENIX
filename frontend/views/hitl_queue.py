"""
HITL Queue View
Human-In-The-Loop review interface for low-confidence triage assessments
"""

import streamlit as st
from utils.api_client import api_client
import pandas as pd
from datetime import datetime
import json

def show():
    """Display HITL queue for doctor review"""
    
    st.title("🔍 HITL Review Queue")
    st.markdown("Review triage assessments flagged for human validation (confidence <65%)")
    st.markdown("---")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
    
    try:
        with st.spinner("Loading HITL queue..."):
            hitl_cases = api_client.get_hitl_queue(st.session_state.access_token)
        
        if not hitl_cases:
            st.success("✅ No pending cases in HITL queue!")
            st.info("All recent triage assessments had confidence ≥65% and were automatically processed.")
            return
        
        # Summary metrics
        st.markdown("### 📊 Queue Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("⏳ Pending Cases", len(hitl_cases))
        
        with col2:
            avg_confidence = sum(case.get('ml_confidence', 0) for case in hitl_cases) / len(hitl_cases)
            st.metric("📉 Avg Confidence", f"{avg_confidence:.1%}")
        
        with col3:
            critical_count = sum(1 for case in hitl_cases if case.get('ml_risk_level') == 'CRITICAL')
            st.metric("🚨 Critical Cases", critical_count)
        
        st.markdown("---")
        
        # Display each HITL case
        for idx, case in enumerate(hitl_cases, 1):
            show_hitl_case(case, idx)
        
        # Auto-refresh logic
        if auto_refresh:
            import time
            time.sleep(30)
            st.rerun()
            
    except PermissionError:
        st.error("🚫 Doctor access required to view HITL queue")
    except Exception as e:
        st.error(f"❌ Error loading HITL queue: {str(e)}")
        st.info("💡 Try refreshing the page")


def show_hitl_case(case: dict, case_number: int):
    """Display individual HITL case with review actions"""
    
    # Extract case data
    decision_id = case.get('decision_id', 'N/A')
    patient_uuid = case.get('patient_uuid', 'N/A')
    patient_name = case.get('patient_name', 'Unknown Patient')
    ml_risk_level = case.get('ml_risk_level', 'UNKNOWN')
    ml_confidence = case.get('ml_confidence', 0.0)
    ml_priority_score = case.get('ml_priority_score', 0.0)
    created_at = case.get('created_at', '')
    vitals = case.get('vitals', {})
    fsm_trace = case.get('fsm_trace', [])
    version_id = case.get('version_id', 0)
    
    # Risk level color mapping
    risk_colors = {
        'CRITICAL': '🔴',
        'HIGH': '🟠',
        'MEDIUM': '🟡',
        'LOW': '🟢',
        'UNKNOWN': '⚪'
    }
    
    risk_emoji = risk_colors.get(ml_risk_level, '⚪')
    
    # Create expander for each case
    with st.expander(f"**Case #{case_number}** | {risk_emoji} {ml_risk_level} | {patient_name} | Confidence: {ml_confidence:.1%}", expanded=(case_number == 1)):
        
        # Case metadata
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"**Patient:** {patient_name}")
            st.markdown(f"**Patient UUID:** `{patient_uuid[:16]}...`")
        
        with col2:
            st.markdown(f"**ML Risk:** {risk_emoji} **{ml_risk_level}**")
            st.markdown(f"**Confidence:** {ml_confidence:.1%}")
        
        with col3:
            st.markdown(f"**Priority Score:** {ml_priority_score:.1f}")
            st.markdown(f"**Submitted:** {format_timestamp(created_at)}")
        
        st.markdown("---")
        
        # Vitals tab and FSM trace tab
        tab1, tab2, tab3 = st.tabs(["📋 Vitals", "🔄 FSM Trace", "⚙️ Actions"])
        
        with tab1:
            show_vitals_section(vitals)
        
        with tab2:
            show_fsm_trace_section(fsm_trace)
        
        with tab3:
            show_actions_section(decision_id, patient_name, ml_risk_level, ml_confidence, version_id)


def show_vitals_section(vitals: dict):
    """Display patient vitals in organized format"""
    
    if not vitals:
        st.warning("⚠️ No vitals data available")
        return
    
    # Vital signs
    st.markdown("#### 🩺 Vital Signs")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Systolic BP", f"{vitals.get('systolic_bp', 'N/A')} mmHg")
        st.metric("Heart Rate", f"{vitals.get('heart_rate', 'N/A')} bpm")
    
    with col2:
        st.metric("Diastolic BP", f"{vitals.get('diastolic_bp', 'N/A')} mmHg")
        st.metric("Temperature", f"{vitals.get('temperature', 'N/A')} °F")
    
    with col3:
        st.metric("Blood Glucose", f"{vitals.get('blood_glucose', 'N/A')} mg/dL")
        st.metric("Gestational Age", f"{vitals.get('gestational_age', 'N/A')} weeks")
    
    # Clinical indicators
    st.markdown("#### 🔬 Clinical Indicators")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Proteinuria:** {vitals.get('proteinuria', 'N/A')}")
        st.markdown(f"**Edema:** {vitals.get('edema', 'N/A')}")
        st.markdown(f"**Previous Complications:** {vitals.get('previous_complications', 'N/A')}")
    
    with col2:
        st.markdown(f"**Vaginal Bleeding:** {vitals.get('vaginal_bleeding', 'N/A')}")
        st.markdown(f"**Fetal Movement:** {vitals.get('fetal_movement', 'N/A')}")
    
    # Symptoms
    symptoms = vitals.get('symptoms', '')
    if symptoms:
        st.markdown("#### 💬 Reported Symptoms")
        st.info(symptoms)


def show_fsm_trace_section(fsm_trace: list):
    """Display FSM execution trace"""
    
    if not fsm_trace:
        st.warning("⚠️ No FSM trace available")
        return
    
    st.markdown("#### 🔄 State Machine Execution Path")
    
    # Display trace as timeline
    for idx, transition in enumerate(fsm_trace, 1):
        from_state = transition.get('from_state', 'UNKNOWN')
        to_state = transition.get('to_state', 'UNKNOWN')
        timestamp = transition.get('timestamp', '')
        metadata = transition.get('metadata', {})
        
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.markdown(f"**Step {idx}**")
            st.caption(format_timestamp(timestamp))
        
        with col2:
            st.markdown(f"`{from_state}` → `{to_state}`")
            
            # Show metadata if available
            if metadata:
                with st.expander("View metadata"):
                    st.json(metadata)
    
    # Highlight terminal state
    if fsm_trace:
        terminal_state = fsm_trace[-1].get('to_state', 'UNKNOWN')
        if terminal_state == 'HITL_HANDOFF':
            st.success(f"✅ Terminal State: **{terminal_state}** - Requires human review")


def show_actions_section(decision_id: str, patient_name: str, ml_risk_level: str, ml_confidence: float, version_id: int):
    """Display action buttons for HITL resolution"""
    
    st.markdown("#### 🎯 Review Decision")
    st.markdown("Select your clinical judgment on this case:")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Confirm ML Assessment", key=f"confirm_{decision_id}", use_container_width=True):
            resolve_hitl_case(decision_id, "CONFIRMED", ml_risk_level, patient_name, version_id, 
                            f"Doctor confirmed ML assessment: {ml_risk_level} (confidence: {ml_confidence:.1%})")
    
    with col2:
        if st.button("⬆️ Escalate to Higher Risk", key=f"escalate_{decision_id}", use_container_width=True):
            escalated_risk = escalate_risk_level(ml_risk_level)
            resolve_hitl_case(decision_id, "ESCALATED", escalated_risk, patient_name, version_id,
                            f"Doctor escalated from {ml_risk_level} to {escalated_risk}")
    
    with col3:
        if st.button("⬇️ Downgrade to Lower Risk", key=f"downgrade_{decision_id}", use_container_width=True):
            downgraded_risk = downgrade_risk_level(ml_risk_level)
            resolve_hitl_case(decision_id, "DOWNGRADED", downgraded_risk, patient_name, version_id,
                            f"Doctor downgraded from {ml_risk_level} to {downgraded_risk}")
    
    st.markdown("---")
    st.caption(f"**Decision ID:** `{decision_id}` | **Version:** {version_id}")


def resolve_hitl_case(decision_id: str, action: str, final_risk_level: str, patient_name: str, version_id: int, notes: str):
    """Send HITL resolution to backend"""
    
    try:
        with st.spinner(f"Processing {action.lower()} action..."):
            result = api_client.resolve_hitl(
                decision_id=decision_id,
                final_risk_level=final_risk_level,
                doctor_notes=notes,
                version_id=version_id,
                token=st.session_state.access_token
            )
        
        st.success(f"✅ {action}: {patient_name} → **{final_risk_level}**")
        st.balloons()
        
        # Wait briefly then reload page
        import time
        time.sleep(2)
        st.rerun()
        
    except ValueError as e:
        if "version conflict" in str(e).lower():
            st.error("⚠️ **Version Conflict**: Another doctor already reviewed this case. Refreshing...")
            import time
            time.sleep(2)
            st.rerun()
        else:
            st.error(f"❌ Resolution failed: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Error resolving case: {str(e)}")
        st.info("💡 Try refreshing the page")


def escalate_risk_level(current_risk: str) -> str:
    """Escalate risk level by one tier"""
    risk_hierarchy = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    try:
        current_idx = risk_hierarchy.index(current_risk)
        return risk_hierarchy[min(current_idx + 1, len(risk_hierarchy) - 1)]
    except ValueError:
        return 'HIGH'  # Default escalation


def downgrade_risk_level(current_risk: str) -> str:
    """Downgrade risk level by one tier"""
    risk_hierarchy = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
    
    try:
        current_idx = risk_hierarchy.index(current_risk)
        return risk_hierarchy[max(current_idx - 1, 0)]
    except ValueError:
        return 'MEDIUM'  # Default downgrade


def format_timestamp(timestamp_str: str) -> str:
    """Format ISO timestamp to readable format"""
    if not timestamp_str:
        return "N/A"
    
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return timestamp_str
