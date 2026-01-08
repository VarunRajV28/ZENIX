"""
Login View
Authentication page with role-based registration and session persistence.
"""

import re
import streamlit as st
import time
from utils.api_client import api_client
from utils.state_manager import update_auth_state
from utils.session_persistence import save_session_to_storage

def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength. Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""

def show():
    """Display the login and registration interface."""
    
    st.title("🤰 MomWatch AI")
    st.subheader("Maternal Health Monitoring System")
    
    # Create two columns for Login and Registration
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
                elif not validate_email(email):
                    st.error("Please enter a valid email address")
                else:
                    try:
                        with st.spinner("Authenticating..."):
                            # Call the backend API
                            response = api_client.login(email, password)
                            
                            # Structure user data for session persistence
                            user_payload = {
                                'role': response['role'],
                                'user_id': response['user_id'],
                                'email': email,
                                'full_name': response['full_name']
                            }
                            
                            # 1. SAVE ENCRYPTED SESSION TO BROWSER COOKIES
                            save_session_to_storage(user_payload, response['access_token'])
                            
                            # 2. UPDATE RUNTIME SESSION STATE
                            update_auth_state(
                                user_data=user_payload,
                                token=response['access_token']
                            )
                            
                            st.success(f"✅ Welcome back, {response['full_name']}!")
                            time.sleep(0.5)
                            st.rerun()
                    
                    except ValueError as e:
                        st.error(f"❌ Login failed: {str(e)}")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
    
    with col2:
        st.markdown("### 📝 Register")
        st.caption("Password must contain: 8+ chars, uppercase, lowercase, and number")
        with st.form("register_form"):
            reg_full_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_password = st.text_input("Password", type="password", key="reg_password")
            reg_password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
            
            reg_role = st.selectbox(
                "I am a:",
                ["asha", "doctor"],
                format_func=lambda x: "👶 ASHA Worker" if x == "asha" else "👨‍⚕️ Doctor"
            )
            
            # Additional role-specific fields
            if reg_role == "asha":
                reg_age = st.number_input("Age", min_value=15, max_value=60, value=28)
                reg_working_weeks = st.number_input("Working Weeks", min_value=0, max_value=42, value=20)
            
            submit_register = st.form_submit_button("Register", use_container_width=True)
            
            if submit_register:
                if not all([reg_full_name, reg_email, reg_password, reg_password_confirm]):
                    st.error("Please fill in all fields")
                elif len(reg_full_name.strip()) < 3:
                    st.error("Full name must be at least 3 characters long")
                elif not validate_email(reg_email):
                    st.error("Please enter a valid email address")
                elif reg_password != reg_password_confirm:
                    st.error("Passwords do not match")
                else:
                    is_valid, error_msg = validate_password(reg_password)
                    if not is_valid:
                        st.error(error_msg)
                    else:
                        try:
                            with st.spinner("Creating account..."):
                                payload = {
                                    "email": reg_email,
                                    "password": reg_password,
                                    "full_name": reg_full_name,
                                    "role": reg_role
                                }
                                
                                if reg_role == "asha":
                                    payload["age"] = reg_age
                                    payload["working_weeks"] = reg_working_weeks
                                
                                # Register user via API
                                response = api_client.register(**payload)
                                st.success("✅ Account created! Please login with your credentials.")
                        
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
    - 📊 Explainable AI with feature importance visualization
    - 🏥 Real-time emergency alerting for healthcare providers
    """)
