"""
XAI Chart Component
Explainable AI visualization showing feature importance
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict

# Medical significance explanations for each feature
FEATURE_EXPLANATIONS = {
    'age': 'Maternal age affects chromosomal abnormality risk and pregnancy complications',
    'systolic_bp': 'High systolic pressure increases preeclampsia risk by 3x',
    'diastolic_bp': 'Elevated diastolic pressure indicates cardiovascular stress',
    'blood_sugar': 'Abnormal glucose levels indicate gestational diabetes risk',
    'body_temperature': 'Elevated temperature may indicate infection or inflammation',
    'heart_rate': 'Abnormal heart rate can signal hemorrhage or cardiac issues',
    'blood_oxygen': 'Low oxygen saturation indicates respiratory distress',
    'gestational_weeks': 'Advanced gestation increases stillbirth and complication risks',
    'BP_Ratio': 'Blood pressure ratio indicates cardiovascular health status',
    'Age_Risk_Score': 'Advanced maternal age classification (≥35 years)',
    'Gestational_Risk': 'Indicates early (<12 weeks) or post-term (>40 weeks) pregnancy'
}

def show_xai_chart(feature_importances: Dict[str, float]):
    """
    Display horizontal bar chart of feature importances
    
    Args:
        feature_importances: Dictionary mapping feature names to importance scores
    """
    
    if not feature_importances:
        st.info("No feature importance data available")
        return
    
    # Sort features by importance (descending)
    sorted_features = sorted(
        feature_importances.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    features = [f[0] for f in sorted_features]
    importances = [f[1] for f in sorted_features]
    
    # Assign colors based on importance threshold
    colors = []
    for imp in importances:
        if imp > 0.2:
            colors.append('#d32f2f')  # Red for high importance
        elif imp > 0.1:
            colors.append('#ff9800')  # Orange for medium importance
        else:
            colors.append('#1976d2')  # Blue for low importance
    
    # Create horizontal bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=features,
        x=importances,
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(color='rgba(0,0,0,0.3)', width=1)
        ),
        text=[f'{imp:.1%}' for imp in importances],
        textposition='outside',
        hovertemplate='<b>%{y}</b><br>' +
                      'Importance: %{x:.1%}<br>' +
                      '<extra></extra>'
    ))
    
    # Add explanations as hover text
    hover_texts = []
    for feature in features:
        explanation = FEATURE_EXPLANATIONS.get(feature, 'Clinical vital sign')
        hover_texts.append(f"<b>{feature}</b><br>{explanation}")
    
    fig.update_layout(
        title={
            'text': '🧠 Feature Importance - What Influenced This Assessment?',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#1f77b4'}
        },
        xaxis_title='Importance Score',
        yaxis_title='Clinical Feature',
        height=max(400, len(features) * 40),
        showlegend=False,
        hovermode='y unified',
        plot_bgcolor='rgba(240,240,240,0.5)',
        paper_bgcolor='white',
        font=dict(size=12)
    )
    
    # Display chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Add explanation section
    with st.expander("ℹ️ How to Interpret This Chart"):
        st.markdown("""
        **Feature Importance** shows which of your health measurements had the most influence on your risk assessment.
        
        - **Red bars (>20%):** Major factors driving the risk level
        - **Orange bars (10-20%):** Moderate contributing factors  
        - **Blue bars (<10%):** Minor contributing factors
        
        **Example Interpretation:**
        - If "systolic_bp" has high importance (red), your blood pressure was a primary concern
        - If "age" has medium importance (orange), maternal age was a moderate risk factor
        - Features with low importance (blue) were within normal ranges
        
        **Clinical Significance:**
        Each feature is explained below:
        """)
        
        for feature, importance in sorted_features[:5]:  # Show top 5
            explanation = FEATURE_EXPLANATIONS.get(feature, 'Clinical vital sign')
            st.markdown(f"- **{feature}** ({importance:.1%}): {explanation}")
