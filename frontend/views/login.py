"""
Login View
Authentication page with role selection
"""

import streamlit as st
from utils.api_client import api_client
from utils.state_manager import update_auth_state

def show():
    """Display login/registration page"""
    
    st.title("🤰 MomWatch AI")
    st.subheader("Maternal Health Monitoring System")
    
    # Create two columns for login and register
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🔐 Login")
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            
            submit_login = st.form_submit_button("Login", use_container_width=True)
            
            if submit_login:
                if not email or not password:
                    st.error("Please fill in all fields")
                else:
                    try:
                        with st.spinner("Authenticating..."):
                            response = api_client.login(email, password)
                            
                            # Update session state
                            update_auth_state(
                                user_data={
                                    'role': response['role'],
                                    'user_id': response['user_id'],
                                    'email': email
                                },
                                token=response['access_token']
                            )
                            
                            st.success(f"✅ Welcome back, {response['full_name']}!")
                            st.rerun()
                    
                    except ValueError as e:
                        st.error(f"❌ Login failed: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
    
    with col2:
        st.markdown("### 📝 Register")
        with st.form("register_form"):
            reg_full_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
            
            reg_role = st.selectbox(
                "I am a:",
                ["mother", "doctor"],
                format_func=lambda x: "👶 Mother" if x == "mother" else "👨‍⚕️ Doctor"
            )
            
            # Additional fields for mother
            if reg_role == "mother":
                reg_age = st.number_input("Age", min_value=15, max_value=60, value=28)
                reg_gestational_weeks = st.number_input("Gestational Weeks", min_value=0, max_value=42, value=20)
            else:
                reg_age = None
                reg_gestational_weeks = None
            
            submit_register = st.form_submit_button("Register", use_container_width=True)
            
            if submit_register:
                if not all([reg_full_name, reg_email, reg_password, reg_password_confirm]):
                    st.error("Please fill in all fields")
                elif reg_password != reg_password_confirm:
                    st.error("Passwords do not match")
                elif len(reg_password) < 8:
                    st.error("Password must be at least 8 characters")
                else:
                    try:
                        with st.spinner("Creating account..."):
                            payload = {
                                "email": reg_email,
                                "password": reg_password,
                                "full_name": reg_full_name,
                                "role": reg_role
                            }
                            
                            if reg_role == "mother":
                                payload["age"] = reg_age
                                payload["gestational_weeks"] = reg_gestational_weeks
                            
                            response = api_client.register(**payload)
                            
                            st.success(f"✅ Account created! Please login with your credentials.")
                    
                    except ValueError as e:
                        st.error(f"❌ Registration failed: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
    
    # Information section
    st.markdown("---")
    st.info("""
    **🏥 About MomWatch AI**
    
    MomWatch AI is an advanced maternal health monitoring system that uses machine learning 
    and clinical rules to assess pregnancy risks in real-time.
    
    **Features:**
    - 🎯 3-layer risk assessment (Validation → Clinical Rules → ML Model)
    - 🔒 Circuit breaker pattern for reliability
    - 🤖 Zudu AI integration for enhanced insights
    - 📊 Explainable AI with feature importance visualization
    - 🏥 Real-time emergency alerting for healthcare providers
    """)
