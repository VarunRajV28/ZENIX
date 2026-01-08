"""
About Page
System overview and information
"""

import streamlit as st

def show():
    """Display about page"""
    
    st.title("🏥 About MomWatch AI")
    
    st.markdown("""
    ## Maternal Health Monitoring System
    
    MomWatch AI is a production-grade, AI-powered maternal health monitoring system designed to 
    reduce pregnancy-related complications through early risk detection and intervention.
    
    ### 🎯 Key Features
    
    #### 1. **3-Layer Risk Assessment Pipeline**
    - **Layer 0 (Sanity Check):** Validates inputs against biological constraints
    - **Layer 1 (Clinical Rules):** WHO evidence-based thresholds for immediate risk flagging
    - **Layer 2 (ML Model):** Random Forest classifier trained on 20,000+ maternal health records
    
    #### 2. **Defensive Engineering**
    - **Circuit Breaker Pattern:** Automatic fallback when ML model fails
    - **Idempotency:** Prevents duplicate submissions using unique request keys
    - **Graceful Degradation:** System remains operational even with partial failures
    
    #### 3. **Explainable AI (XAI)**
    - Feature importance visualization shows which vitals influenced the risk assessment
    - Clinical notes explain medical reasoning in human-readable language
    - Confidence scores provide transparency in predictions
    
    #### 4. **Zudu AI Integration**
    - Advanced NLP-powered maternal health insights
    - Clinical decision support recommendations
    - Risk factor explanations in natural language
    
    #### 5. **Real-time Emergency Alerting**
    - Automatic CRITICAL patient flagging for healthcare providers
    - Priority scoring algorithm for efficient triage
    - 30-second auto-refresh for emergency feed
    
    ### 🏗️ System Architecture
    
    ```
    Frontend (Streamlit) ←→ Backend (FastAPI) ←→ MongoDB
                                    ↓
                            Risk Assessment Engine
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
            Clinical Rules Engine          ML Model (RandomForest)
                    ↓                               ↓
                    └───────────────┬───────────────┘
                                    ↓
                              Zudu AI Enhancement
                                    ↓
                            Final Risk Assessment
    ```
    
    ### 🛡️ Security Features
    - JWT-based authentication with token expiration
    - Bcrypt password hashing
    - CORS protection
    - Input validation at API boundary
    - Role-based access control (Mother/Doctor)
    
    ### 📊 Clinical Thresholds
    
    **CRITICAL Flags (Bypass ML):**
    - Hypertensive Crisis: BP ≥140/90 mmHg
    - Hypoxia: SpO2 <94%
    - Severe Tachycardia: HR >120 bpm
    - Severe Hypoglycemia: Blood sugar <3.0 mmol/L
    - Severe Hyperglycemia: Blood sugar >11.0 mmol/L
    
    **Risk Factors:**
    - Advanced Maternal Age: ≥35 years
    - Post-term Pregnancy: >40 weeks
    - Hyperthermia: Temperature >38.5°C
    
    ### 🔬 ML Model Performance
    - **Algorithm:** Random Forest Classifier (200 trees)
    - **Training Data:** 20,000 synthetic maternal health records
    - **Features:** 8 clinical vitals + engineered features
    - **Accuracy:** ~92% on test set
    - **Feature Importance:** Blood pressure, age, gestational weeks
    
    ### 🐳 Technology Stack
    - **Backend:** FastAPI, Motor (async MongoDB), Pydantic
    - **Frontend:** Streamlit, Plotly
    - **Database:** MongoDB 6.0+
    - **ML:** Scikit-learn, Joblib
    - **AI Enhancement:** Zudu AI API
    - **Deployment:** Docker, Docker Compose
    
    ### 👥 User Roles
    
    **Mother:**
    - Submit health vitals for risk assessment
    - View personal health dashboard with trends
    - Access health passport with complete history
    - Update profile information
    
    **Doctor:**
    - Monitor all patients in real-time
    - View emergency feed with CRITICAL patients
    - Access detailed patient histories
    - Priority-based patient sorting
    
    ### 📞 Support
    For technical support or questions, please contact:
    - Email: support@momwatch.ai
    - Emergency Hotline: 1-800-MOMWATCH
    
    ### 📄 License & Credits
    MomWatch AI is built with open-source technologies and is intended for educational 
    and research purposes. Always consult qualified healthcare professionals for medical decisions.
    
    **Dataset Reference:** 
    Maternal Health Risk Data Set - Kaggle
    
    **AI Partner:** 
    Zudu AI - Advanced Maternal Health NLP
    """)
    
    st.markdown("---")
    st.info("💙 MomWatch AI - Making pregnancy safer, one assessment at a time.")
