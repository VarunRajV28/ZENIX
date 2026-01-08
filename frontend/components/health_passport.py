"""
Health Passport Component
Comprehensive health history visualization
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List
from datetime import datetime

def show_health_passport(passport_data: Dict):
    """
    Display comprehensive health passport with patient summary and history
    
    Args:
        passport_data: Dictionary containing patient profile and assessment history
    """
    
    st.markdown("## 📖 Health Passport")
    
    # Patient Summary Card
    profile = passport_data.get('profile', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Age", f"{profile.get('age', 'N/A')} years")
    with col2:
        st.metric("Gestational Week", f"Week {profile.get('gestational_weeks', 'N/A')}")
    with col3:
        due_date = profile.get('estimated_due_date', 'N/A')
        st.metric("Estimated Due Date", due_date)
    with col4:
        total_assessments = len(passport_data.get('history', []))
        st.metric("Total Assessments", total_assessments)
    
    st.markdown("---")
    
    # Summary Statistics
    st.markdown("### 📊 Summary Statistics")
    
    history = passport_data.get('history', [])
    
    if history:
        risk_counts = {
            'LOW': 0,
            'MEDIUM': 0,
            'HIGH': 0,
            'CRITICAL': 0
        }
        
        for assessment in history:
            risk_level = assessment.get('risk_level', 'UNKNOWN')
            if risk_level in risk_counts:
                risk_counts[risk_level] += 1
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("✅ Low Risk", risk_counts['LOW'])
        with col2:
            st.metric("⚠️ Medium Risk", risk_counts['MEDIUM'])
        with col3:
            st.metric("🚨 High Risk", risk_counts['HIGH'])
        with col4:
            st.metric("🆘 Critical", risk_counts['CRITICAL'])
        
        # Risk distribution pie chart
        fig_pie = go.Figure(data=[go.Pie(
            labels=list(risk_counts.keys()),
            values=list(risk_counts.values()),
            marker=dict(colors=['#4caf50', '#ff9800', '#f44336', '#b71c1c']),
            hole=0.4
        )])
        
        fig_pie.update_layout(
            title="Risk Level Distribution",
            height=400,
            showlegend=True
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        
        # Vitals Timeline
        st.markdown("### 📈 Vitals Timeline")
        
        # Convert history to DataFrame
        df_history = []
        for h in history:
            vitals = h.get('vitals', {})
            df_history.append({
                'timestamp': h.get('timestamp'),
                'systolic_bp': vitals.get('systolic_bp'),
                'diastolic_bp': vitals.get('diastolic_bp'),
                'heart_rate': vitals.get('heart_rate'),
                'blood_sugar': vitals.get('blood_sugar'),
                'blood_oxygen': vitals.get('blood_oxygen'),
                'body_temperature': vitals.get('body_temperature'),
                'risk_level': h.get('risk_level')
            })
        
        df = pd.DataFrame(df_history).sort_values('timestamp')
        
        # Blood Pressure Timeline
        fig_bp = go.Figure()
        
        fig_bp.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['systolic_bp'],
            mode='lines+markers',
            name='Systolic BP',
            line=dict(color='#d32f2f', width=2),
            marker=dict(size=8)
        ))
        
        fig_bp.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['diastolic_bp'],
            mode='lines+markers',
            name='Diastolic BP',
            line=dict(color='#1976d2', width=2),
            marker=dict(size=8)
        ))
        
        # Add threshold lines
        fig_bp.add_hline(y=140, line_dash="dash", line_color="red", 
                         annotation_text="Hypertensive Threshold (140)")
        fig_bp.add_hline(y=90, line_dash="dash", line_color="orange",
                         annotation_text="Diastolic Threshold (90)")
        
        fig_bp.update_layout(
            title="Blood Pressure Over Time",
            xaxis_title="Date",
            yaxis_title="Blood Pressure (mmHg)",
            height=400,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_bp, use_container_width=True)
        
        # Additional Vitals
        col1, col2 = st.columns(2)
        
        with col1:
            # Heart Rate
            fig_hr = go.Figure()
            fig_hr.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['heart_rate'],
                mode='lines+markers',
                name='Heart Rate',
                line=dict(color='#7b1fa2', width=2),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(123, 31, 162, 0.1)'
            ))
            
            fig_hr.add_hline(y=120, line_dash="dash", line_color="red",
                            annotation_text="Tachycardia Threshold")
            
            fig_hr.update_layout(
                title="Heart Rate Trend",
                xaxis_title="Date",
                yaxis_title="Heart Rate (bpm)",
                height=300
            )
            
            st.plotly_chart(fig_hr, use_container_width=True)
            
            # Blood Oxygen
            fig_o2 = go.Figure()
            fig_o2.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['blood_oxygen'],
                mode='lines+markers',
                name='SpO2',
                line=dict(color='#0288d1', width=2),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(2, 136, 209, 0.1)'
            ))
            
            fig_o2.add_hline(y=94, line_dash="dash", line_color="red",
                            annotation_text="Hypoxia Threshold")
            
            fig_o2.update_layout(
                title="Blood Oxygen Saturation",
                xaxis_title="Date",
                yaxis_title="SpO2 (%)",
                height=300
            )
            
            st.plotly_chart(fig_o2, use_container_width=True)
        
        with col2:
            # Blood Sugar
            fig_bs = go.Figure()
            fig_bs.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['blood_sugar'],
                mode='lines+markers',
                name='Blood Sugar',
                line=dict(color='#388e3c', width=2),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(56, 142, 60, 0.1)'
            ))
            
            fig_bs.add_hline(y=11.0, line_dash="dash", line_color="red",
                            annotation_text="Hyperglycemia Threshold")
            fig_bs.add_hline(y=3.0, line_dash="dash", line_color="orange",
                            annotation_text="Hypoglycemia Threshold")
            
            fig_bs.update_layout(
                title="Blood Sugar Levels",
                xaxis_title="Date",
                yaxis_title="Blood Sugar (mmol/L)",
                height=300
            )
            
            st.plotly_chart(fig_bs, use_container_width=True)
            
            # Body Temperature
            fig_temp = go.Figure()
            fig_temp.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['body_temperature'],
                mode='lines+markers',
                name='Temperature',
                line=dict(color='#f57c00', width=2),
                marker=dict(size=8),
                fill='tozeroy',
                fillcolor='rgba(245, 124, 0, 0.1)'
            ))
            
            fig_temp.add_hline(y=38.5, line_dash="dash", line_color="red",
                              annotation_text="Fever Threshold")
            
            fig_temp.update_layout(
                title="Body Temperature",
                xaxis_title="Date",
                yaxis_title="Temperature (°C)",
                height=300
            )
            
            st.plotly_chart(fig_temp, use_container_width=True)
        
        st.markdown("---")
        
        # Assessment History Table
        st.markdown("### 📋 Assessment History")
        
        table_data = []
        for h in history[-20:]:  # Show last 20 assessments
            table_data.append({
                'Date': h.get('timestamp'),
                'Risk Level': h.get('risk_level'),
                'Confidence': f"{h.get('confidence', 0):.1%}",
                'Alerts': len(h.get('alerts', [])),
                'Engine': h.get('engine_source', 'N/A')
            })
        
        df_table = pd.DataFrame(table_data)
        st.dataframe(df_table, use_container_width=True, hide_index=True)
    
    else:
        st.info("📋 No assessment history available yet.")
    
    # Pre-existing Conditions
    if profile.get('pre_existing_conditions'):
        st.markdown("---")
        st.markdown("### 🏥 Pre-existing Conditions")
        st.info(profile['pre_existing_conditions'])
