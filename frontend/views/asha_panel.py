"""
ASHA Worker Panel View
Dashboard for ASHA workers to manage multiple pregnant women
"""

import streamlit as st
from utils.api_client import api_client
from components.vitals_form import show_vitals_form
from components.alert_card import show_alert_card
import pandas as pd
from datetime import datetime

def show():
    """Display ASHA worker dashboard"""
    
    st.title("🏥 ASHA Worker Dashboard")
    st.markdown(f"Welcome, **`{st.session_state.user_email}`**")
    st.markdown("---")
    
    # Dashboard statistics
    show_statistics()
    
    st.markdown("---")
    
    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🩺 Submit Patient Vitals", "📋 All Patients"])
    
    with tab1:
        show_dashboard_overview()
    
    with tab2:
        show_submit_vitals_section()
    
    with tab3:
        show_all_patients()

def show_statistics():
    """Display ASHA worker statistics"""
    try:
        # Clear force refresh flag if set
        if 'force_refresh' in st.session_state:
            del st.session_state['force_refresh']
        
        history = api_client.get_history(st.session_state.access_token)
        
        # Calculate statistics
        total_patients = len(history)
        critical_count = sum(1 for h in history if h.get('risk_level') == 'CRITICAL')
        high_count = sum(1 for h in history if h.get('risk_level') == 'HIGH')
        recent_assessments = sum(1 for h in history if h.get('timestamp', '').startswith(datetime.now().strftime('%Y-%m-%d')))
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👥 Total Patients", total_patients)
        
        with col2:
            st.metric("🆘 Critical Cases", critical_count, delta=None if critical_count == 0 else f"{critical_count} need attention", delta_color="inverse")
        
        with col3:
            st.metric("⚠️ High Risk Cases", high_count, delta=None if high_count == 0 else f"{high_count} need monitoring", delta_color="inverse")
        
        with col4:
            st.metric("📅 Today's Assessments", recent_assessments)
    
    except Exception as e:
        st.info("Loading statistics...")

def show_dashboard_overview():
    """Show overview of recent patient assessments"""
    st.markdown("## 📊 Recent Patient Assessments")
    
    try:
        # Fetch fresh data every time
        history = api_client.get_history(st.session_state.access_token)
        
        if not history:
            st.info("📝 No patient data uploaded yet. Start by submitting patient vitals in the 'Submit Patient Vitals' tab.")
            return
        
        # Show recent assessments
        st.markdown("### 🕒 Latest 10 Assessments")
        
        for assessment in history[:10]:
            risk_level = assessment.get('risk_level', 'UNKNOWN')
            timestamp = assessment.get('timestamp', 'N/A')
            confidence = assessment.get('confidence', 0)
            
            # Extract patient name from vitals
            vitals = assessment.get('vitals', {})
            patient_name = vitals.get('patient_name', 'Unknown Patient')
            
            # Color based on risk
            if risk_level == 'CRITICAL':
                color = '#ffcdd2'
                icon = '🆘'
            elif risk_level == 'HIGH':
                color = '#ffe0b2'
                icon = '⚠️'
            elif risk_level == 'MEDIUM':
                color = '#fff9c4'
                icon = '⚡'
            else:
                color = '#c8e6c9'
                icon = '✅'
            
            with st.container():
                st.markdown(f"""
                <div style="background-color: {color}; padding: 15px; border-radius: 10px; margin-bottom: 10px;">
                    <h4>{icon} {patient_name}</h4>
                    <p><strong>Assessment:</strong> {timestamp}</p>
                    <p><strong>Risk Level:</strong> {risk_level} | <strong>Confidence:</strong> {confidence:.1%}</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                # Extract vitals from nested dict
                vitals = assessment.get('vitals', {})
                
                with col1:
                    st.markdown("**Vitals:**")
                    st.write(f"• Age: {vitals.get('age', 'N/A')} years")
                    st.write(f"• BP: {vitals.get('bp', 'N/A')} mmHg")
                    st.write(f"• Heart Rate: {vitals.get('heart_rate', 'N/A')} bpm")
                
                with col2:
                    st.markdown("**More Vitals:**")
                    st.write(f"• SpO2: {vitals.get('blood_oxygen', 'N/A')}%")
                    st.write(f"• Blood Sugar: {vitals.get('blood_sugar', 'N/A')} mmol/L")
                    st.write(f"• Temp: {vitals.get('body_temp', 'N/A')}°C")
                
                with col3:
                    st.markdown("**Pregnancy Info:**")
                    st.write(f"• Gestational Weeks: {vitals.get('gestational_weeks', 'N/A')}")
                    if assessment.get('alerts'):
                        st.markdown("**⚠️ Alerts:**")
                        for alert in assessment['alerts'][:2]:
                            st.error(f"• {alert}")
                
                st.markdown("---")
    
    except Exception as e:
        st.error(f"❌ Error loading dashboard: {str(e)}")

def show_submit_vitals_section():
    """Section for submitting new patient vitals"""
    st.markdown("## 🩺 Submit Patient Vitals")
    st.markdown("Fill in the health measurements for a pregnant woman under your care.")
    
    vitals_data = show_vitals_form()
    
    if st.button("🚀 Submit Assessment", type="primary", use_container_width=True):
        if vitals_data:
            with st.spinner("Analyzing patient health..."):
                try:
                    patient_name = vitals_data.pop('patient_name', 'Unknown')
                    
                    # Store patient name in symptoms/notes field
                    existing_symptoms = vitals_data.get('symptoms', '')
                    # Ensure existing_symptoms is a string
                    if not isinstance(existing_symptoms, str):
                        existing_symptoms = str(existing_symptoms) if existing_symptoms else ''
                    
                    if existing_symptoms:
                        vitals_data['symptoms'] = f"Patient: {patient_name} | Symptoms: {existing_symptoms}"
                    else:
                        vitals_data['symptoms'] = f"Patient: {patient_name}"
                    
                    # Generate idempotency key
                    import uuid
                    idempotency_key = str(uuid.uuid4())
                    
                    result = api_client.submit_triage(
                        vitals=vitals_data,
                        token=st.session_state.access_token,
                        idempotency_key=idempotency_key
                    )
                    
                    # Display result with patient name
                    st.success(f"✅ Assessment completed for **{patient_name}**!")
                    
                    show_alert_card(result)
                    
                    # Provide manual refresh option
                    st.info("💡 **Tip:** Switch to 'Dashboard' or 'All Patients' tab to view the updated records.")
                    
                    if st.button("🔄 Refresh Dashboard Now", type="secondary"):
                        st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Assessment failed: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
        else:
            st.warning("⚠️ Please fill all required fields correctly")

def show_all_patients():
    """Show complete list of all patients"""
    st.markdown("## 📋 Complete Patient Records")
    
    try:
        # Fetch fresh data every time
        history = api_client.get_history(st.session_state.access_token)
        
        if not history:
            st.info("📝 No patient records found.")
            return
        
        st.write(f"**Total Records:** {len(history)}")
        
        # Filter options
        col1, col2 = st.columns(2)
        
        with col1:
            risk_filter = st.selectbox(
                "Filter by Risk Level",
                ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
            )
        
        with col2:
            sort_order = st.selectbox(
                "Sort by",
                ["Most Recent", "Oldest First", "Highest Risk"]
            )
        
        # Apply filters
        filtered_history = history
        if risk_filter != "All":
            filtered_history = [h for h in history if h.get('risk_level') == risk_filter]
        
        # Apply sorting
        if sort_order == "Oldest First":
            filtered_history = list(reversed(filtered_history))
        elif sort_order == "Highest Risk":
            risk_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
            filtered_history = sorted(filtered_history, key=lambda x: risk_order.get(x.get('risk_level', 'LOW'), 4))
        
        st.write(f"**Showing:** {len(filtered_history)} records")
        
        # Create DataFrame for display
        if filtered_history:
            df_data = []
            for idx, record in enumerate(filtered_history, 1):
                # Extract patient name from vitals
                vitals = record.get('vitals', {})
                patient_name = vitals.get('patient_name', 'Unknown')
                
                df_data.append({
                    '#': idx,
                    'Patient': patient_name,
                    'Age': vitals.get('age', 'N/A'),
                    'Risk': record.get('risk_level', 'N/A'),
                    'BP': vitals.get('bp', 'N/A'),
                    'HR': vitals.get('heart_rate', 'N/A'),
                    'SpO2': f"{vitals.get('blood_oxygen', 'N/A')}%",
                    'Weeks': vitals.get('gestational_weeks', 'N/A'),
                    'Date': str(record.get('timestamp', 'N/A'))[:10] if record.get('timestamp') else 'N/A'
                })
            
            df = pd.DataFrame(df_data)
            
            # Color-coded display
            def color_risk(row):
                risk = row['Risk']
                if risk == 'CRITICAL':
                    return ['background-color: #ffcdd2'] * len(row)
                elif risk == 'HIGH':
                    return ['background-color: #ffe0b2'] * len(row)
                elif risk == 'MEDIUM':
                    return ['background-color: #fff9c4'] * len(row)
                else:
                    return ['background-color: #c8e6c9'] * len(row)
            
            styled_df = df.style.apply(color_risk, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Download option
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Records (CSV)",
                data=csv,
                file_name=f"asha_worker_records_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    except Exception as e:
        st.error(f"❌ Error loading patient records: {str(e)}")
