"""
Contact Page
Support information and feedback form
"""

import streamlit as st

def show():
    """Display contact page"""
    
    st.title("📞 Contact & Support")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ## 🏥 Emergency Contact
        
        **If you are experiencing a medical emergency, call emergency services immediately.**
        
        ### Hotlines:
        - **Emergency:** 911 (US) / 112 (EU)
        - **MomWatch Support:** 1-800-MOMWATCH
        - **Maternal Health Hotline:** 1-800-311-BABY
        
        ### Email Support:
        - General Inquiries: info@momwatch.ai
        - Technical Support: support@momwatch.ai
        - Medical Questions: clinical@momwatch.ai
        
        ### Office Hours:
        Monday - Friday: 9:00 AM - 6:00 PM EST
        Saturday: 10:00 AM - 4:00 PM EST
        Sunday: Closed (Emergency support available 24/7)
        
        ### Mailing Address:
        MomWatch AI  
        123 Healthcare Drive  
        Medical Innovation District  
        Boston, MA 02101  
        United States
        """)
    
    with col2:
        st.markdown("## 💬 Feedback Form")
        
        with st.form("feedback_form"):
            name = st.text_input("Your Name")
            email = st.text_input("Email Address")
            
            feedback_type = st.selectbox(
                "Feedback Type",
                ["General Feedback", "Bug Report", "Feature Request", "Clinical Question", "Technical Support"]
            )
            
            message = st.text_area("Message", height=200)
            
            submitted = st.form_submit_button("📤 Send Feedback", use_container_width=True)
            
            if submitted:
                if not all([name, email, message]):
                    st.error("Please fill in all fields")
                else:
                    # In production, this would send to backend API
                    st.success(f"""
                    ✅ Thank you for your feedback, {name}!
                    
                    We have received your {feedback_type.lower()} and will respond to {email} 
                    within 24-48 hours.
                    
                    Reference ID: FB-{hash(email + message) % 100000:05d}
                    """)
    
    st.markdown("---")
    
    st.markdown("""
    ## 🌐 Additional Resources
    
    ### Educational Materials:
    - [Understanding Pregnancy Risk Factors](https://www.cdc.gov/pregnancy)
    - [WHO Maternal Health Guidelines](https://www.who.int/health-topics/maternal-health)
    - [Preeclampsia Foundation](https://www.preeclampsia.org/)
    
    ### For Healthcare Providers:
    - [API Documentation](http://localhost:8000/docs)
    - [Integration Guide](#)
    - [Clinical Validation Studies](#)
    
    ### Community:
    - [MomWatch User Forum](#)
    - [FAQ & Knowledge Base](#)
    - [Video Tutorials](#)
    """)
    
    st.info("🔒 **Privacy Note:** All communications are encrypted and HIPAA compliant.")
