"""
Doctor Panel View
Dashboard for healthcare providers to monitor patients
"""

import streamlit as st
from utils.api_client import api_client
from components.alert_card import show_alert_card
import pandas as pd
from datetime import datetime
import time

def show():
    """Display doctor dashboard"""
    
    st.title("👨‍⚕️ Doctor Dashboard")
    st.markdown(f"Logged in as: **{st.session_state.user_email}**")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
    
    # Emergency feed section (always at top)
    show_emergency_feed()
    
    st.markdown("---")
    
    # Priority patient list
    show_priority_patients()
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(30)
        st.rerun()

def show_emergency_feed():
    """Display CRITICAL patients requiring immediate attention"""
    st.markdown("## 🆘 EMERGENCY FEED")
    
    try:
        with st.spinner("Fetching critical patients..."):
            emergency_patients = api_client.get_emergency_feed(st.session_state.access_token)
        
        if not emergency_patients:
            st.success("✅ No critical emergencies at this time")
            return
        
        # Red alert banner
        st.error(f"⚠️ {len(emergency_patients)} CRITICAL patient(s) require immediate attention!")
        
        # Display each critical patient
        for patient in emergency_patients:
            with st.container():
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 20px; border-radius: 10px; 
                            border-left: 5px solid red; margin-bottom: 15px;">
                    <h3 style="color: darkred;">🆘 Patient #{patient['patient_id'][:8].upper()}</h3>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Patient Info:**")
                    st.write(f"Age: {patient.get('age', 'N/A')}")
                    st.write(f"Gestational Weeks: {patient.get('gestational_weeks', 'N/A')}")
                    st.write(f"Last Assessment: {patient.get('timestamp', 'N/A')}")
                
                with col2:
                    st.markdown("**Vitals Snapshot:**")
                    vitals = patient.get('vitals', {})
                    st.write(f"BP: {vitals.get('systolic_bp')}/{vitals.get('diastolic_bp')} mmHg")
                    st.write(f"HR: {vitals.get('heart_rate')} bpm")
                    st.write(f"SpO2: {vitals.get('blood_oxygen')}%")
                    st.write(f"Blood Sugar: {vitals.get('blood_sugar')} mmol/L")
                
                with col3:
                    st.markdown("**Alerts:**")
                    for alert in patient.get('alerts', []):
                        st.error(f"🚨 {alert}")
                    
                    if st.button(f"View Full Details", key=f"detail_{patient['patient_id']}", 
                                use_container_width=True):
                        show_patient_detail_modal(patient['patient_id'])
                
                # Clinical notes
                if patient.get('clinical_notes'):
                    with st.expander("📋 Clinical Notes"):
                        for note in patient['clinical_notes']:
                            st.markdown(f"- {note}")
                
                st.markdown("---")
    
    except PermissionError:
        st.error("❌ Doctor access required")
    except Exception as e:
        st.error(f"❌ Error fetching emergency feed: {str(e)}")

def show_priority_patients():
    """Display all patients sorted by priority score"""
    st.markdown("## 📋 Priority Triage List")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filter_option = st.selectbox(
            "Filter by Risk",
            ["All Patients", "Critical Only", "High+ Risk", "Medium+ Risk"]
        )
    
    try:
        with st.spinner("Loading patient list..."):
            patients = api_client.get_priority_patients(st.session_state.access_token)
        
        if not patients:
            st.info("📋 No patients in the system")
            return
        
        # Apply filter
        if filter_option == "Critical Only":
            patients = [p for p in patients if p['risk_level'] == 'CRITICAL']
        elif filter_option == "High+ Risk":
            patients = [p for p in patients if p['risk_level'] in ['CRITICAL', 'HIGH']]
        elif filter_option == "Medium+ Risk":
            patients = [p for p in patients if p['risk_level'] in ['CRITICAL', 'HIGH', 'MEDIUM']]
        
        st.write(f"Showing {len(patients)} patient(s)")
        
        # Convert to DataFrame for display
        df_data = []
        for p in patients:
            df_data.append({
                'Patient ID': p['patient_id'][:8].upper(),
                'Risk Level': p['risk_level'],
                'Priority Score': f"{p['priority_score']:.2f}",
                'Age': p.get('age', 'N/A'),
                'Weeks': p.get('gestational_weeks', 'N/A'),
                'Last Checkup': p.get('last_checkup', 'N/A'),
                'Alerts': len(p.get('alerts', []))
            })
        
        df = pd.DataFrame(df_data)
        
        # Color-coded display
        def color_row(row):
            if row['Risk Level'] == 'CRITICAL':
                return ['background-color: #ffcdd2'] * len(row)
            elif row['Risk Level'] == 'HIGH':
                return ['background-color: #ffe0b2'] * len(row)
            elif row['Risk Level'] == 'MEDIUM':
                return ['background-color: #fff9c4'] * len(row)
            else:
                return ['background-color: #c8e6c9'] * len(row)
        
        styled_df = df.style.apply(color_row, axis=1)
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # Expandable details for each patient
        st.markdown("### 🔍 Patient Details")
        selected_patient_id = st.selectbox(
            "Select patient to view details:",
            [p['patient_id'] for p in patients],
            format_func=lambda x: f"Patient #{x[:8].upper()}"
        )
        
        if selected_patient_id:
            show_patient_detail_inline(selected_patient_id)
    
    except Exception as e:
        st.error(f"❌ Error loading patients: {str(e)}")

def show_patient_detail_inline(patient_id: str):
    """Display detailed patient information inline"""
    try:
        with st.spinner("Loading patient details..."):
            details = api_client.get_patient_details(patient_id, st.session_state.access_token)
        
        st.markdown(f"#### Patient #{patient_id[:8].upper()} - Full History")
        
        # Summary card
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Current Risk", details.get('current_risk_level', 'N/A'))
        with col2:
            st.metric("Total Assessments", details.get('total_assessments', 0))
        with col3:
            st.metric("Critical Events", details.get('critical_count', 0))
        with col4:
            st.metric("Age", details.get('age', 'N/A'))
        
        # History timeline
        if details.get('history'):
            st.markdown("**Assessment Timeline:**")
            
            history_df = pd.DataFrame(details['history'])
            
            # Show last 10 assessments
            for idx, row in history_df.head(10).iterrows():
                with st.expander(f"{row['timestamp']} - {row['risk_level']}", expanded=(idx == 0)):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Vitals:**")
                        vitals = row.get('vitals', {})
                        st.write(f"BP: {vitals.get('systolic_bp')}/{vitals.get('diastolic_bp')} mmHg")
                        st.write(f"HR: {vitals.get('heart_rate')} bpm")
                        st.write(f"SpO2: {vitals.get('blood_oxygen')}%")
                        st.write(f"Temp: {vitals.get('body_temperature')}°C")
                        st.write(f"Blood Sugar: {vitals.get('blood_sugar')} mmol/L")
                    
                    with col2:
                        st.markdown("**Assessment:**")
                        st.write(f"Risk: {row['risk_level']}")
                        st.write(f"Confidence: {row['confidence']:.1%}")
                        st.write(f"Engine: {row.get('engine_source', 'N/A')}")
                        
                        if row.get('alerts'):
                            st.markdown("**Alerts:**")
                            for alert in row['alerts']:
                                st.error(f"⚠️ {alert}")
            
            # Download option
            csv = history_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Patient History (CSV)",
                data=csv,
                file_name=f"patient_{patient_id[:8]}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    except Exception as e:
        st.error(f"❌ Error loading patient details: {str(e)}")

def show_patient_detail_modal(patient_id: str):
    """Show patient details in modal (placeholder for future implementation)"""
    st.info(f"Detailed view for patient {patient_id[:8]} - Feature coming soon!")
