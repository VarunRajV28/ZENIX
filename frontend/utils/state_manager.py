"""
Session State Management
Centralized initialization and management of Streamlit session state
"""

import streamlit as st

def initialize_session_state():
    """Initialize all required session state variables"""
    
    # Authentication state
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = False
    
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    if 'access_token' not in st.session_state:
        st.session_state.access_token = None
    
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    
    if 'full_name' not in st.session_state:
        st.session_state.full_name = None
    
    # UI state
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "login"
    
    # Cache for API responses
    if 'cache' not in st.session_state:
        st.session_state.cache = {}
    
    # Error messages
    if 'last_error' not in st.session_state:
        st.session_state.last_error = None

def clear_session_state():
    """Clear all session state (logout)"""
    st.session_state.authentication_status = False
    st.session_state.user_role = None
    st.session_state.user_id = None
    st.session_state.access_token = None
    st.session_state.user_email = None
    st.session_state.full_name = None
    st.session_state.current_page = "login"
    st.session_state.cache = {}
    st.session_state.last_error = None

def update_auth_state(user_data: dict, token: str):
    """Update session state after successful login"""
    st.session_state.authentication_status = True
    st.session_state.user_role = user_data.get('role')
    st.session_state.user_id = user_data.get('user_id')
    st.session_state.user_email = user_data.get('email')
    st.session_state.full_name = user_data.get('full_name')
    st.session_state.access_token = token
    st.session_state.last_error = None
