"""
Mother Panel View
Dashboard for pregnant women to monitor their health
"""

import streamlit as st
from utils.api_client import api_client
from components.vitals_form import show_vitals_form
from components.xai_chart import show_xai_chart
from components.health_passport import show_health_passport
from components.alert_card import show_alert_card
import uuid
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

def show():
    """Display mother dashboard with tabs"""
    
    st.title("👶 Mother Dashboard")
    st.markdown(f"Welcome, **{st.session_state.user_email}**")
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🩺 Submit Vitals", "📖 Health Passport", "👤 Profile"])
    
    with tab1:
        show_dashboard_tab()
    
    with tab2:
        show_triage_submission_tab()
    
    with tab3:
        show_health_passport_tab()
    
    with tab4:
        show_profile_tab()

def show_dashboard_tab():
    """Display overview dashboard with latest assessment and trends"""
    st.subheader("Health Overview")
    
    try:
        # Fetch history
        with st.spinner("Loading your health data..."):
            history = api_client.get_history(st.session_state.access_token)
        
        if not history:
            st.info("📋 No health assessments yet. Submit your vitals in the 'Submit Vitals' tab to get started!")
            return
        
        # Display latest assessment
        latest = history[0]
        
        # Risk level card
        risk_level = latest['risk_level']
        risk_colors = {
            'LOW': ('green', '✅'),
            'MEDIUM': ('orange', '⚠️'),
            'HIGH': ('red', '🚨'),
            'CRITICAL': ('darkred', '🆘')
        }
        
        color, icon = risk_colors.get(risk_level, ('gray', '❓'))
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"""
            <div style="background-color: {color}; padding: 20px; border-radius: 10px; color: white;">
                <h2>{icon} Current Risk Level: {risk_level}</h2>
                <p>Confidence: {latest['confidence']:.1%}</p>
                <p>Last assessed: {latest['timestamp']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.metric("Total Assessments", len(history))
        
        with col3:
            critical_count = sum(1 for h in history if h['risk_level'] == 'CRITICAL')
            st.metric("Critical Alerts", critical_count, delta=None)
        
        # Alerts section
        if latest.get('alerts'):
            st.markdown("### 🚨 Active Alerts")
            for alert in latest['alerts']:
                show_alert_card(alert, latest.get('clinical_notes', []))
        
        # Trends visualization
        st.markdown("### 📈 Vitals Trends (Last 30 Days)")
        
        if len(history) > 1:
            # Convert to DataFrame
            df = pd.DataFrame([{
                'timestamp': h['timestamp'],
                'systolic_bp': h.get('vitals', {}).get('systolic_bp'),
                'diastolic_bp': h.get('vitals', {}).get('diastolic_bp'),
                'heart_rate': h.get('vitals', {}).get('heart_rate'),
                'blood_sugar': h.get('vitals', {}).get('blood_sugar'),
                'blood_oxygen': h.get('vitals', {}).get('blood_oxygen'),
                'body_temperature': h.get('vitals', {}).get('body_temperature')
            } for h in reversed(history[-30:])])
            
            # Blood pressure chart
            fig_bp = go.Figure()
            fig_bp.add_trace(go.Scatter(x=df['timestamp'], y=df['systolic_bp'], 
                                        mode='lines+markers', name='Systolic BP',
                                        line=dict(color='red', width=2)))
            fig_bp.add_trace(go.Scatter(x=df['timestamp'], y=df['diastolic_bp'], 
                                        mode='lines+markers', name='Diastolic BP',
                                        line=dict(color='blue', width=2)))
            fig_bp.update_layout(title="Blood Pressure Trend", 
                                xaxis_title="Date", yaxis_title="mmHg",
                                hovermode='x unified')
            st.plotly_chart(fig_bp, use_container_width=True)
            
            # Other vitals
            col1, col2 = st.columns(2)
            
            with col1:
                fig_hr = go.Figure()
                fig_hr.add_trace(go.Scatter(x=df['timestamp'], y=df['heart_rate'],
                                           mode='lines+markers', name='Heart Rate',
                                           line=dict(color='purple', width=2)))
                fig_hr.update_layout(title="Heart Rate Trend",
                                    xaxis_title="Date", yaxis_title="bpm")
                st.plotly_chart(fig_hr, use_container_width=True)
            
            with col2:
                fig_bs = go.Figure()
                fig_bs.add_trace(go.Scatter(x=df['timestamp'], y=df['blood_sugar'],
                                           mode='lines+markers', name='Blood Sugar',
                                           line=dict(color='green', width=2)))
                fig_bs.update_layout(title="Blood Sugar Trend",
                                    xaxis_title="Date", yaxis_title="mmol/L")
                st.plotly_chart(fig_bs, use_container_width=True)
        else:
            st.info("Submit more assessments to see trends")
    
    except Exception as e:
        st.error(f"❌ Error loading dashboard: {str(e)}")

def show_triage_submission_tab():
    """Display vitals submission form"""
    st.subheader("Submit Your Vitals")
    
    st.info("📝 Fill in your current health measurements. All fields are required.")
    
    # Use the reusable vitals form component
    vitals_data = show_vitals_form()
    
    if vitals_data:
        # Submit button
        if st.button("🔍 Assess Risk", type="primary", use_container_width=True):
            try:
                # Generate idempotency key
                idempotency_key = str(uuid.uuid4())
                
                with st.spinner("🤖 Analyzing your health data..."):
                    result = api_client.submit_triage(
                        vitals_data,
                        st.session_state.access_token,
                        idempotency_key
                    )
                
                # Display results
                st.success("✅ Assessment Complete!")
                
                # Risk level display
                risk_level = result['risk_level']
                risk_colors = {
                    'LOW': 'green',
                    'MEDIUM': 'orange',
                    'HIGH': 'red',
                    'CRITICAL': 'darkred'
                }
                
                st.markdown(f"""
                <div style="background-color: {risk_colors.get(risk_level, 'gray')}; 
                            padding: 30px; border-radius: 15px; color: white; text-align: center;">
                    <h1>Risk Level: {risk_level}</h1>
                    <h3>Confidence: {result['confidence']:.1%}</h3>
                    <p>Engine: {result['engine_source']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown("---")
                
                # Alerts
                if result.get('alerts'):
                    st.markdown("### 🚨 Clinical Alerts")
                    for alert in result['alerts']:
                        show_alert_card(alert, result.get('clinical_notes', []))
                
                # Clinical notes
                if result.get('clinical_notes'):
                    st.markdown("### 📋 Clinical Notes")
                    for note in result['clinical_notes']:
                        st.markdown(f"- {note}")
                
                # XAI Chart
                if result.get('feature_importances'):
                    st.markdown("### 🧠 What Influenced This Assessment?")
                    show_xai_chart(result['feature_importances'])
                
                # Zudu AI Insights
                if result.get('zudu_insights') and result['zudu_insights'].get('clinical_insights'):
                    with st.expander("🤖 AI-Powered Clinical Insights (Zudu AI)"):
                        insights = result['zudu_insights']
                        st.markdown(f"**Clinical Analysis:** {insights.get('clinical_insights', 'N/A')}")
                        
                        if insights.get('recommended_actions'):
                            st.markdown("**Recommended Actions:**")
                            for action in insights['recommended_actions']:
                                st.markdown(f"- {action}")
                        
                        if insights.get('urgency_score'):
                            st.metric("Urgency Score", f"{insights['urgency_score']}/10")
                
                # System info
                with st.expander("ℹ️ System Information"):
                    st.json({
                        'timestamp': result.get('timestamp'),
                        'processing_time_ms': result.get('processing_time_ms'),
                        'fallback_active': result.get('fallback_active', False),
                        'engine_source': result.get('engine_source')
                    })
            
            except ValueError as e:
                st.error(f"❌ Validation Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ Assessment failed: {str(e)}")

def show_health_passport_tab():
    """Display health passport with comprehensive history"""
    st.subheader("📖 Health Passport")
    
    try:
        with st.spinner("Generating health passport..."):
            passport = api_client.get_health_passport(st.session_state.access_token)
        
        show_health_passport(passport)
        
        # Download option
        if passport.get('history'):
            df = pd.DataFrame(passport['history'])
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Full History (CSV)",
                data=csv,
                file_name=f"health_passport_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    
    except Exception as e:
        st.error(f"❌ Error loading health passport: {str(e)}")

def show_profile_tab():
    """Display and edit profile"""
    st.subheader("👤 Profile Settings")
    
    try:
        with st.spinner("Loading profile..."):
            profile = api_client.get_profile(st.session_state.access_token)
        
        with st.form("profile_form"):
            st.text_input("Email", value=profile['email'], disabled=True)
            full_name = st.text_input("Full Name", value=profile['full_name'])
            age = st.number_input("Age", min_value=15, max_value=60, value=profile.get('age', 28))
            gestational_weeks = st.number_input("Gestational Weeks", min_value=0, max_value=42, 
                                                value=profile.get('gestational_weeks', 20))
            
            pre_existing = st.text_area("Pre-existing Conditions (optional)", 
                                       value=profile.get('pre_existing_conditions', ''))
            
            submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)
            
            if submitted:
                try:
                    update_data = {
                        "full_name": full_name,
                        "age": age,
                        "gestational_weeks": gestational_weeks,
                        "pre_existing_conditions": pre_existing
                    }
                    
                    api_client.update_profile(update_data, st.session_state.access_token)
                    st.success("✅ Profile updated successfully!")
                    st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Update failed: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Error loading profile: {str(e)}")
