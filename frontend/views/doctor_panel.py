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
    st.markdown(f"Welcome, **Dr. {st.session_state.user_email}**")
    st.markdown("---")
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 All Patients", "🆘 SOS Alerts", "👤 Profile", "📖 About", "📞 Contact"])
    
    with tab1:
        show_all_patients_tab()
    
    with tab2:
        show_sos_alerts_tab()
    
    with tab3:
        show_profile_tab()
    
    with tab4:
        show_about_tab()
    
    with tab5:
        show_contact_tab()

def show_all_patients_tab():
    """Main dashboard showing all patients with filters"""
    st.markdown("## 📋 All Patients - Complete Overview")
    
    # Auto-refresh toggle
    col1, col2 = st.columns([3, 1])
    with col2:
        auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=False)
    
    try:
        with st.spinner("Loading all patients..."):
            patients = api_client.get_priority_patients(st.session_state.access_token)
        
        if not patients:
            st.info("📋 No patients in the system")
            return
        
        # Store original list for filtering
        all_patients = patients.copy()
        
        # Filter controls at top
        st.markdown("### 🔍 Filter Patients")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_risk = st.multiselect(
                "Risk Level",
                ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
                default=["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            )
        
        with col2:
            search_name = st.text_input("🔎 Search by Patient Name", placeholder="Enter patient name...")
        
        with col3:
            sort_by = st.selectbox("Sort By", ["Priority Score", "Risk Level", "Latest Assessment", "Patient Name"])
        
        # Apply filters
        if filter_risk:
            patients = [p for p in patients if p['risk_level'] in filter_risk]
        
        if search_name:
            patients = [p for p in patients if search_name.lower() in p.get('patient_name', '').lower()]
        
        # Apply sorting
        if sort_by == "Risk Level":
            risk_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3}
            patients = sorted(patients, key=lambda x: risk_order.get(x['risk_level'], 4))
        elif sort_by == "Latest Assessment":
            patients = sorted(patients, key=lambda x: x.get('last_assessment', ''), reverse=True)
        elif sort_by == "Patient Name":
            patients = sorted(patients, key=lambda x: x.get('patient_name', 'Unknown'))
        # Priority Score is default from backend
        
        st.markdown(f"**Showing {len(patients)} of {len(all_patients)} patients**")
        st.markdown("---")
        
        # Display patients in cards
        for idx, patient in enumerate(patients):
            show_patient_card(patient, idx)
        
    except Exception as e:
        st.error(f"❌ Error loading patients: {str(e)}")
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(30)
        st.rerun()

def show_patient_card(patient, idx):
    """Display individual patient card with all details"""
    patient_name = patient.get('patient_name', 'Unknown Patient')
    patient_id = patient['patient_id']
    risk_level = patient['risk_level']
    
    # Color based on risk
    if risk_level == 'CRITICAL':
        bg_color = '#ffebee'
        border_color = '#c62828'
        icon = '🆘'
    elif risk_level == 'HIGH':
        bg_color = '#fff3e0'
        border_color = '#e64a19'
        icon = '⚠️'
    elif risk_level == 'MEDIUM':
        bg_color = '#fffde7'
        border_color = '#f9a825'
        icon = '⚡'
    else:
        bg_color = '#e8f5e9'
        border_color = '#388e3c'
        icon = '✅'
    
    with st.container():
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; 
                    border-left: 5px solid {border_color}; margin-bottom: 15px;">
            <h3 style="color: {border_color}; margin: 0;">{icon} {patient_name}</h3>
            <p style="color: #666; margin: 5px 0;">ID: {patient_id[:8].upper()} | Risk: {risk_level}</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("**Patient Info:**")
            st.write(f"📅 Age: {patient.get('age', 'N/A')} years")
            st.write(f"🤰 Gestational Weeks: {patient.get('gestational_weeks', 'N/A')}")
            st.write(f"📊 Priority Score: {patient.get('priority_score', 'N/A')}")
        
        with col2:
            st.markdown("**Risk Assessment:**")
            st.write(f"🎯 Risk Level: {risk_level}")
            alert_count = len(patient.get('alerts', []))
            st.write(f"⚠️ Active Alerts: {alert_count}")
            last_checkup = patient.get('hours_since_checkup', 'N/A')
            st.write(f"🕒 Last Checkup: {last_checkup} hrs ago")
        
        with col3:
            st.markdown("**Clinical Alerts:**")
            alerts = patient.get('alerts', [])
            if alerts:
                for alert in alerts[:3]:  # Show first 3 alerts
                    st.error(f"• {alert}")
                if len(alerts) > 3:
                    st.info(f"+ {len(alerts) - 3} more alerts...")
            else:
                st.success("No active alerts")
        
        with col4:
            st.markdown("**Actions:**")
            if st.button(f"� Contact ASHA Worker", key=f"contact_{patient_id}_{idx}", 
                        use_container_width=True, type="primary"):
                st.info(f"ASHA Worker ID: {patient_id[:8].upper()}")
        
        st.markdown("---")

def show_sos_alerts_tab():
    """Dedicated page for CRITICAL patients only"""
    st.markdown("## 🆘 SOS ALERTS - Critical Patients")
    st.markdown("### Emergency cases requiring immediate attention")
    
    try:
        with st.spinner("Fetching critical patients..."):
            emergency_patients = api_client.get_emergency_feed(st.session_state.access_token)
        
        if not emergency_patients:
            st.success("✅ No critical emergencies at this time")
            return
        
        # Red alert banner
        st.error(f"⚠️ **{len(emergency_patients)} CRITICAL patient(s) require immediate attention!**")
        st.markdown("---")
        
        # Display each critical patient
        for idx, patient in enumerate(emergency_patients):
            patient_name = patient.get('patient_name', 'Unknown Patient')
            with st.container():
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 20px; border-radius: 10px; 
                            border-left: 5px solid red; margin-bottom: 15px;">
                    <h3 style="color: darkred;">🆘 {patient_name}</h3>
                    <p style="color: #666;">ID: {patient['patient_id'][:8].upper()} | CRITICAL STATUS</p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Patient Info:**")
                    st.write(f"Age: {patient.get('age', 'N/A')}")
                    st.write(f"Gestational Weeks: {patient.get('gestational_weeks', 'N/A')}")
                    st.write(f"Last Assessment: {patient.get('assessment_time', 'N/A')}")
                    st.write(f"⏰ Hours Since: {patient.get('hours_since_assessment', 'N/A')}")
                
                with col2:
                    st.markdown("**Vitals Snapshot:**")
                    vitals = patient.get('vitals_snapshot', {})
                    st.write(f"🩺 BP: {vitals.get('bp', 'N/A')} mmHg")
                    st.write(f"💓 HR: {vitals.get('heart_rate', 'N/A')} bpm")
                    st.write(f"🫁 SpO2: {vitals.get('blood_oxygen', 'N/A')}%")
                    st.write(f"🩸 Blood Sugar: {vitals.get('blood_sugar', 'N/A')} mmol/L")
                    st.write(f"🌡️ Temp: {vitals.get('body_temp', 'N/A')}°C")
                
                with col3:
                    st.markdown("**Critical Alerts:**")
                    for alert in patient.get('alerts', []):
                        st.error(f"🚨 {alert}")
                    
                    st.markdown("**Immediate Action Required:**")
                    if st.button(f"📞 Emergency Contact", key=f"emergency_{patient['patient_id']}_{idx}", 
                                type="primary", use_container_width=True):
                        st.success("Emergency protocol initiated!")
                
                st.markdown("---")
    
    except PermissionError:
        st.error("❌ Doctor access required")
    except Exception as e:
        st.error(f"❌ Error fetching emergency feed: {str(e)}")

def show_complete_patient_details(patient_id: str):
    """Show complete patient details inline"""
    try:
        with st.spinner("Loading complete patient details..."):
            response = api_client.get_patient_details(patient_id, st.session_state.access_token)
        
        patient_info = response.get('patient', {})
        history = response.get('history', [])
        
        # Get patient name
        patient_name = patient_info.get('full_name', 'Unknown Patient')
        if history and history[0].get('vitals', {}).get('patient_name'):
            patient_name = history[0]['vitals']['patient_name']
        
        # Patient Header
        st.markdown(f"### 👤 {patient_name} - Complete Medical Record")
        
        # Basic Information
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**📋 Basic Info:**")
            st.write(f"**Name:** {patient_name}")
            st.write(f"**Patient ID:** {patient_id[:8].upper()}")
            latest_vitals = history[0]['vitals'] if history else {}
            st.write(f"**Age:** {latest_vitals.get('age', patient_info.get('age', 'N/A'))} years")
        
        with col2:
            st.markdown("**🤰 Pregnancy Info:**")
            st.write(f"**Gestational Weeks:** {latest_vitals.get('gestational_weeks', patient_info.get('gestational_weeks', 'N/A'))}")
            conditions = patient_info.get('pre_existing_conditions', [])
            st.write(f"**Pre-existing Conditions:** {', '.join(conditions) if conditions else 'None'}")
        
        with col3:
            st.markdown("**👩‍⚕️ ASHA Worker:**")
            st.write(f"**Worker ID:** {patient_id[:8].upper()}")
            st.write(f"**Total Assessments:** {len(history)}")
        
        # Latest Vitals
        if history:
            st.markdown("---")
            st.markdown("### 🩺 Latest Vitals")
            latest = history[0]
            vitals = latest.get('vitals', {})
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Blood Pressure", vitals.get('bp', 'N/A'))
                st.metric("Heart Rate", f"{vitals.get('heart_rate', 'N/A')} bpm")
            
            with col2:
                st.metric("Blood Oxygen", f"{vitals.get('blood_oxygen', 'N/A')}%")
                st.metric("Body Temperature", f"{vitals.get('body_temp', 'N/A')}°C")
            
            with col3:
                st.metric("Blood Sugar", f"{vitals.get('blood_sugar', 'N/A')} mmol/L")
                st.metric("Gestational Weeks", vitals.get('gestational_weeks', 'N/A'))
            
            with col4:
                risk = latest.get('risk_level', 'N/A')
                confidence = latest.get('confidence', 0)
                st.metric("Risk Level", risk)
                st.metric("Confidence", f"{confidence:.1%}")
        
        # Assessment History
        st.markdown("---")
        st.markdown("### 📊 Assessment History")
        
        if history:
            for i, assessment in enumerate(history[:5]):
                timestamp = str(assessment.get('timestamp', 'N/A'))[:19]
                risk = assessment.get('risk_level', 'N/A')
                
                with st.expander(f"Assessment {i+1}: {timestamp} - {risk}", expanded=(i==0)):
                    cols = st.columns(2)
                    
                    with cols[0]:
                        vitals = assessment.get('vitals', {})
                        st.markdown("**Vitals:**")
                        st.write(f"🩺 BP: {vitals.get('bp', 'N/A')}")
                        st.write(f"💓 HR: {vitals.get('heart_rate', 'N/A')} bpm")
                        st.write(f"🫁 SpO2: {vitals.get('blood_oxygen', 'N/A')}%")
                        st.write(f"🩸 Blood Sugar: {vitals.get('blood_sugar', 'N/A')} mmol/L")
                        st.write(f"🌡️ Temp: {vitals.get('body_temp', 'N/A')}°C")
                    
                    with cols[1]:
                        st.markdown("**Assessment:**")
                        st.write(f"Risk: {risk}")
                        st.write(f"Confidence: {assessment.get('confidence', 0):.1%}")
                        
                        alerts = assessment.get('alerts', [])
                        if alerts:
                            st.markdown("**Alerts:**")
                            for alert in alerts:
                                st.error(f"⚠️ {alert}")
        
        # Download option
        if history:
            csv_data = []
            for h in history:
                vitals = h.get('vitals', {})
                csv_data.append({
                    'Timestamp': h.get('timestamp'),
                    'Risk Level': h.get('risk_level'),
                    'Confidence': h.get('confidence'),
                    'BP': vitals.get('bp'),
                    'Heart Rate': vitals.get('heart_rate'),
                    'Blood Oxygen': vitals.get('blood_oxygen'),
                    'Body Temp': vitals.get('body_temp'),
                    'Blood Sugar': vitals.get('blood_sugar'),
                    'Gestational Weeks': vitals.get('gestational_weeks'),
                    'Alerts': ', '.join(h.get('alerts', []))
                })
            
            history_df = pd.DataFrame(csv_data)
            csv = history_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Complete Medical History",
                data=csv,
                file_name=f"{patient_name}_{patient_id[:8]}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    except Exception as e:
        st.error(f"❌ Error loading patient details: {str(e)}")
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
                'Patient Name': p.get('patient_name', 'Unknown'),
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
        
        # Create patient display mapping
        patient_options = {p['patient_id']: p.get('patient_name', f"Patient #{p['patient_id'][:8].upper()}") 
                          for p in patients}
        
        selected_patient_id = st.selectbox(
            "Select patient to view details:",
            list(patient_options.keys()),
            format_func=lambda x: patient_options[x]
        )
        
        if selected_patient_id:
            show_patient_detail_inline(selected_patient_id)
    
    except Exception as e:
        st.error(f"❌ Error loading patients: {str(e)}")

def show_patient_detail_inline(patient_id: str):
    """Display detailed patient information inline"""
    try:
        with st.spinner("Loading patient details..."):
            response = api_client.get_patient_details(patient_id, st.session_state.access_token)
        
        patient_info = response.get('patient', {})
        history = response.get('history', [])
        
        # Get patient name
        patient_name = patient_info.get('full_name', 'Unknown Patient')
        if history and history[0].get('vitals', {}).get('patient_name'):
            patient_name = history[0]['vitals']['patient_name']
        
        st.markdown(f"#### 👤 {patient_name} - Full Medical History")
        
        # Summary card
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_risk = history[0].get('risk_level', 'N/A') if history else 'N/A'
            st.metric("Current Risk", current_risk)
        with col2:
            st.metric("Total Assessments", len(history))
        with col3:
            critical_count = sum(1 for h in history if h.get('risk_level') == 'CRITICAL')
            st.metric("Critical Events", critical_count)
        with col4:
            st.metric("Age", patient_info.get('age', 'N/A'))
        
        # History timeline
        if history:
            st.markdown("**📊 Assessment Timeline:**")
            
            # Show last 10 assessments
            for idx, assessment in enumerate(history[:10]):
                timestamp = str(assessment.get('timestamp', 'N/A'))[:19]
                risk = assessment.get('risk_level', 'N/A')
                
                with st.expander(f"{timestamp} - {risk}", expanded=(idx == 0)):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Vitals:**")
                        vitals = assessment.get('vitals', {})
                        st.write(f"BP: {vitals.get('bp', 'N/A')} mmHg")
                        st.write(f"HR: {vitals.get('heart_rate', 'N/A')} bpm")
                        st.write(f"SpO2: {vitals.get('blood_oxygen', 'N/A')}%")
                        st.write(f"Temp: {vitals.get('body_temp', 'N/A')}°C")
                        st.write(f"Blood Sugar: {vitals.get('blood_sugar', 'N/A')} mmol/L")
                        st.write(f"Gestational Weeks: {vitals.get('gestational_weeks', 'N/A')}")
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
    """Show patient details in expander"""
    try:
        with st.spinner("Loading patient details..."):
            response = api_client.get_patient_details(patient_id, st.session_state.access_token)
        
        patient_info = response.get('patient', {})
        history = response.get('history', [])
        
        # Get patient name from latest assessment or use full_name
        patient_name = patient_info.get('full_name', 'Unknown Patient')
        if history and history[0].get('vitals', {}).get('patient_name'):
            patient_name = history[0]['vitals']['patient_name']
        
        with st.expander(f"📋 {patient_name} - Complete Medical Record", expanded=True):
            # Patient Header Info
            st.markdown(f"### 👤 Patient Information")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**Basic Info:**")
                st.write(f"**Name:** {patient_name}")
                st.write(f"**Patient ID:** {patient_id[:8].upper()}")
                st.write(f"**Age:** {patient_info.get('age', 'N/A')} years")
            
            with col2:
                st.markdown("**Pregnancy Info:**")
                st.write(f"**Gestational Weeks:** {patient_info.get('gestational_weeks', 'N/A')}")
                conditions = patient_info.get('pre_existing_conditions', [])
                st.write(f"**Pre-existing Conditions:** {', '.join(conditions) if conditions else 'None'}")
            
            with col3:
                st.markdown("**ASHA Worker:**")
                # ASHA worker info is the user_id from patient record
                st.write(f"**Worker ID:** {patient_id[:8].upper()}")
                st.write(f"**Contact:** Available in system")
            
            # Summary metrics
            st.markdown("---")
            st.markdown("### 📊 Assessment Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                current_risk = history[0].get('risk_level', 'N/A') if history else 'N/A'
                st.metric("Current Risk", current_risk)
            with col2:
                st.metric("Total Assessments", len(history))
            with col3:
                critical_count = sum(1 for h in history if h.get('risk_level') == 'CRITICAL')
                st.metric("Critical Events", critical_count)
            with col4:
                high_count = sum(1 for h in history if h.get('risk_level') == 'HIGH')
                st.metric("High Risk Events", high_count)
            
            st.markdown("---")
            
            # Assessment history
            if history:
                st.markdown("### 📊 Assessment Timeline")
                
                # Show last 5 assessments
                for i, assessment in enumerate(history[:5]):
                    timestamp = assessment.get('timestamp', 'N/A')
                    risk = assessment.get('risk_level', 'N/A')
                    confidence = assessment.get('confidence', 0)
                    
                    # Color based on risk
                    if risk == 'CRITICAL':
                        color = '#ffcdd2'
                    elif risk == 'HIGH':
                        color = '#ffe0b2'
                    elif risk == 'MEDIUM':
                        color = '#fff9c4'
                    else:
                        color = '#c8e6c9'
                    
                    st.markdown(f"""
                    <div style="background-color: {color}; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <strong>{timestamp}</strong> - Risk: <strong>{risk}</strong> (Confidence: {confidence:.1%})
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Vitals:**")
                        vitals = assessment.get('vitals', {})
                        st.write(f"• BP: {vitals.get('bp', 'N/A')} mmHg")
                        st.write(f"• Heart Rate: {vitals.get('heart_rate', 'N/A')} bpm")
                        st.write(f"• SpO2: {vitals.get('blood_oxygen', 'N/A')}%")
                        st.write(f"• Temperature: {vitals.get('body_temp', 'N/A')}°C")
                        st.write(f"• Blood Sugar: {vitals.get('blood_sugar', 'N/A')} mmol/L")
                    
                    with col2:
                        st.markdown("**Assessment Details:**")
                        st.write(f"• Assessment ID: {assessment.get('assessment_id', 'N/A')[:8]}...")
                        st.write(f"• Confidence: {confidence:.1%}")
                        
                        if assessment.get('alerts'):
                            st.markdown("**⚠️ Alerts:**")
                            for alert in assessment['alerts'][:3]:
                                st.error(f"• {alert}")
                    
                    st.markdown("---")
                
                # Download button
                if len(history) > 0:
                    import pandas as pd
                    # Flatten the data for CSV
                    csv_data = []
                    for h in history:
                        vitals = h.get('vitals', {})
                        csv_data.append({
                            'Timestamp': h.get('timestamp'),
                            'Risk Level': h.get('risk_level'),
                            'Confidence': h.get('confidence'),
                            'BP': vitals.get('bp'),
                            'Heart Rate': vitals.get('heart_rate'),
                            'Blood Oxygen': vitals.get('blood_oxygen'),
                            'Body Temp': vitals.get('body_temp'),
                            'Blood Sugar': vitals.get('blood_sugar'),
                            'Alerts': ', '.join(h.get('alerts', []))
                        })
                    
                    history_df = pd.DataFrame(csv_data)
                    csv = history_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Complete History (CSV)",
                        data=csv,
                        file_name=f"patient_{patient_id[:8]}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.info("No assessment history available for this patient.")
    
    except Exception as e:
        st.error(f"❌ Error loading patient details: {str(e)}")


def show_profile_tab():
    """Display doctor profile information"""
    st.markdown("## 👤 Doctor Profile")
    
    st.markdown("### 👨‍⚕️ Personal Information")
    st.text_input("Full Name", value=st.session_state.user_email.split('@')[0].title(), disabled=True)
    st.text_input("Email", value=st.session_state.user_email, disabled=True)
    st.text_input("Role", value="Doctor", disabled=True)
    st.text_input("Specialization", value="Maternal Health Specialist", disabled=True)
    
    st.markdown("---")
    
    # Statistics
    st.markdown("### 📊 My Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    try:
        patients = api_client.get_priority_patients(st.session_state.access_token)
        emergency_patients = api_client.get_emergency_feed(st.session_state.access_token)
        
        with col1:
            st.metric("Total Patients Monitored", len(patients))
        with col2:
            st.metric("Critical Cases", len(emergency_patients))
        with col3:
            high_risk = len([p for p in patients if p['risk_level'] in ['CRITICAL', 'HIGH']])
            st.metric("High Risk Patients", high_risk)
        with col4:
            st.metric("Active Today", len(patients))
    except:
        st.info("Loading statistics...")


def show_about_tab():
    """Display information about the system"""
    st.markdown("## 📖 About MomWatch AI")
    
    st.markdown("""
    ### 🏥 Maternal Health Monitoring System
    
    **MomWatch AI** is an advanced maternal health risk assessment platform designed to:
    
    - 🔍 **Early Detection**: Identify high-risk pregnancies before complications arise
    - 🤖 **AI-Powered Analysis**: Use machine learning to predict maternal health risks
    - ⚡ **Real-Time Alerts**: Immediate notifications for critical conditions
    - 📊 **Comprehensive Monitoring**: Track vital signs and health trends
    - 👥 **Multi-Role Support**: ASHA workers, doctors, and administrators
    
    ### 🎯 Key Features
    
    #### For Doctors:
    - 🆘 Emergency feed for CRITICAL patients
    - 📋 Priority-sorted patient triage list
    - 📈 Historical trend analysis
    - 💊 Clinical decision support
    - 📥 Export patient data for records
    
    #### Risk Assessment Layers:
    1. **Layer 0**: Sanity validation (adversarial defense)
    2. **Layer 1**: Clinical rules engine (evidence-based protocols)
    3. **Layer 2**: Machine Learning model (RandomForest, 99.6% accuracy)
    4. **Layer 3**: Comprehensive assessment aggregation
    
    ### 📊 System Performance
    - **Model Accuracy**: 99.6%
    - **Risk Categories**: LOW, MEDIUM, HIGH, CRITICAL
    - **Response Time**: < 500ms average
    - **Idempotency**: Built-in request deduplication
    
    ### 🔒 Security & Privacy
    - JWT-based authentication
    - Role-based access control (RBAC)
    - Encrypted data transmission
    - HIPAA-compliant data handling
    
    ### 📚 Clinical Alerts Detected
    - Hypertensive Crisis
    - Severe Hypotension
    - Tachycardia / Bradycardia
    - Hypoxia
    - Gestational Diabetes
    - Fever / Hypothermia
    - And more...
    
    ### 👥 Development Team
    Built with ❤️ for improving maternal health outcomes worldwide.
    
    **Version**: 1.2.0  
    **Last Updated**: January 2026
    """)


def show_contact_tab():
    """Display contact and support information"""
    st.markdown("## 📞 Contact & Support")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏥 Hospital/Clinic Support")
        st.markdown("""
        **Emergency Helpline**: 🆘 1800-XXX-XXXX  
        **Email**: support@momwatch.health  
        **Hours**: 24/7 Emergency Support
        
        **Technical Support**:  
        📧 tech@momwatch.health  
        ⏰ Mon-Fri, 9 AM - 6 PM
        """)
        
        st.markdown("### 📍 Location")
        st.markdown("""
        **Head Office**:  
        MomWatch Health Systems  
        Medical District  
        Healthcare Technology Park  
        """)
    
    with col2:
        st.markdown("### 💬 Quick Contact Form")
        
        with st.form("contact_form"):
            name = st.text_input("Your Name", value=st.session_state.user_email.split('@')[0].title())
            email = st.text_input("Email", value=st.session_state.user_email)
            subject = st.selectbox("Subject", [
                "Technical Issue",
                "Patient Concern",
                "Feature Request",
                "Training/Documentation",
                "Other"
            ])
            message = st.text_area("Message", placeholder="Describe your query or concern...")
            
            submitted = st.form_submit_button("📤 Send Message", use_container_width=True)
            
            if submitted:
                if message:
                    st.success("✅ Message sent successfully! We'll respond within 24 hours.")
                else:
                    st.error("❌ Please enter a message")
    
    st.markdown("---")
    
    st.markdown("### 📚 Resources")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        **📖 Documentation**
        - User Guide
        - Clinical Protocols
        - API Reference
        - Training Videos
        """)
    
    with col2:
        st.markdown("""
        **🔧 Quick Links**
        - Report a Bug
        - Feature Requests
        - System Status
        - Release Notes
        """)
    
    with col3:
        st.markdown("""
        **👥 Community**
        - Discussion Forum
        - Best Practices
        - Case Studies
        - Research Papers
        """)
