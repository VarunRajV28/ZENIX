"""
MomWatch AI - Frontend Entry Point
Multi-page Streamlit application with role-based navigation
"""

import streamlit as st
from utils.state_manager import initialize_session_state, clear_session_state
from views import login, asha_panel, doctor_panel, about, contact, hitl_queue

# Configure page
st.set_page_config(
    page_title="MomWatch AI - Maternal Health Monitoring",
    page_icon="🤰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
initialize_session_state()

def show_sidebar():
    """Display sidebar with navigation and logout"""
    with st.sidebar:
        st.title("🤰 MomWatch AI")
        st.markdown("---")
        
        if st.session_state.authentication_status:
            st.success(f"👤 Logged in as: **{st.session_state.user_role.upper()}**")
            st.markdown(f"**User ID:** {st.session_state.user_id[:8]}...")
            
            st.markdown("---")
            st.subheader("Navigation")
            
            # Role-based navigation
            if st.session_state.user_role == "asha":
                page = st.radio(
                    "Go to",
                    ["Dashboard", "About", "Contact"],
                    label_visibility="collapsed"
                )
            else:  # doctor role
                page = st.radio(
                    "Go to",
                    ["Doctor Dashboard", "HITL Queue", "About", "Contact"],
                    label_visibility="collapsed"
                )
            
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                clear_session_state()
                st.rerun()
            
            return page
        else:
            st.info("Please login to continue")
            return None

def main():
    """Main application router"""
    
    if not st.session_state.authentication_status:
        # Show login page for unauthenticated users
        login.show()
    else:
        # Show sidebar and get selected page
        selected_page = show_sidebar()
        
        # Route to appropriate page
        if st.session_state.user_role == "asha":
            if selected_page == "Dashboard":
                asha_panel.show()
            elif selected_page == "About":
                about.show()
            elif selected_page == "Contact":
                contact.show()
        elif st.session_state.user_role == "doctor":
            if selected_page == "Doctor Dashboard":
                doctor_panel.show()
            elif selected_page == "HITL Queue":
                hitl_queue.show()
            elif selected_page == "About":
                about.show()
            elif selected_page == "Contact":
                contact.show()

if __name__ == "__main__":
    main()
