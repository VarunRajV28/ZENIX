"""
Alert Card Component
Display clinical alerts with icons and color coding
"""

import streamlit as st
from typing import List

# Alert definitions with icons and descriptions
ALERT_DEFINITIONS = {
    'HYPERTENSIVE_CRISIS': {
        'icon': '🔴',
        'title': 'Hypertensive Crisis',
        'color': '#c62828',
        'description': 'Blood pressure ≥140/90 mmHg indicates preeclampsia risk'
    },
    'HYPOXIA': {
        'icon': '💨',
        'title': 'Hypoxia',
        'color': '#d32f2f',
        'description': 'Low oxygen saturation (<94%) indicates respiratory distress'
    },
    'TACHYCARDIA': {
        'icon': '💓',
        'title': 'Tachycardia',
        'color': '#e64a19',
        'description': 'Elevated heart rate (>120 bpm) may indicate hemorrhage or infection'
    },
    'HYPERTHERMIA': {
        'icon': '🌡️',
        'title': 'Hyperthermia',
        'color': '#f57c00',
        'description': 'High temperature (>38.5°C) suggests possible infection'
    },
    'HYPOGLYCEMIA': {
        'icon': '⬇️',
        'title': 'Hypoglycemia',
        'color': '#ffa000',
        'description': 'Low blood sugar (<3.0 mmol/L) increases seizure risk'
    },
    'HYPERGLYCEMIA': {
        'icon': '⬆️',
        'title': 'Hyperglycemia',
        'color': '#ff8f00',
        'description': 'High blood sugar (>11.0 mmol/L) indicates gestational diabetes crisis'
    },
    'ADVANCED_MATERNAL_AGE': {
        'icon': '👵',
        'title': 'Advanced Maternal Age',
        'color': '#fbc02d',
        'description': 'Age ≥35 years increases chromosomal abnormality risk'
    },
    'POST_TERM_PREGNANCY': {
        'icon': '📅',
        'title': 'Post-term Pregnancy',
        'color': '#afb42b',
        'description': 'Pregnancy >40 weeks increases stillbirth risk'
    }
}

def show_alert_card(alert_type: str, clinical_notes: List[str] = None):
    """
    Display a clinical alert card with color coding
    
    Args:
        alert_type: Type of alert (e.g., 'HYPERTENSIVE_CRISIS')
        clinical_notes: Optional list of clinical notes to display
    """
    
    alert_info = ALERT_DEFINITIONS.get(alert_type, {
        'icon': '⚠️',
        'title': alert_type.replace('_', ' ').title(),
        'color': '#757575',
        'description': 'Clinical alert detected'
    })
    
    st.markdown(f"""
    <div style="background-color: {alert_info['color']}20; 
                border-left: 5px solid {alert_info['color']}; 
                padding: 15px; 
                border-radius: 5px; 
                margin: 10px 0;">
        <h4 style="color: {alert_info['color']}; margin: 0;">
            {alert_info['icon']} {alert_info['title']}
        </h4>
        <p style="margin: 5px 0 0 0; color: #424242;">
            {alert_info['description']}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show relevant clinical notes
    if clinical_notes:
        relevant_notes = [note for note in clinical_notes if alert_type.lower() in note.lower()]
        if relevant_notes:
            for note in relevant_notes:
                st.markdown(f"- {note}")
