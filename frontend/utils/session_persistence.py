"""
Session Persistence with localStorage
Uses browser localStorage to persist authentication across page refreshes
"""

import streamlit as st
import streamlit.components.v1 as components

def save_session_to_storage(user_data: dict, token: str):
    """Save session to browser localStorage"""
    import json
    
    session_data = {
        'role': user_data.get('role'),
        'user_id': user_data.get('user_id'),
        'email': user_data.get('email'),
        'full_name': user_data.get('full_name'),
        'token': token,
        'authenticated': True
    }
    
    # Save to localStorage using JavaScript
    session_json = json.dumps(session_data).replace('"', '\\"')
    components.html(
        f"""
        <script>
            localStorage.setItem('momwatch_session', '{session_json}');
            window.parent.postMessage({{type: 'session_saved'}}, '*');
        </script>
        """,
        height=0,
    )

def clear_session_storage():
    """Clear session from browser localStorage"""
    components.html(
        """
        <script>
            localStorage.removeItem('momwatch_session');
            window.parent.postMessage({type: 'session_cleared'}, '*');
        </script>
        """,
        height=0,
    )

def get_session_js():
    """Return JavaScript code to retrieve session from localStorage"""
    return """
    <script>
        const session = localStorage.getItem('momwatch_session');
        if (session) {
            try {
                const data = JSON.parse(session);
                window.parent.postMessage({
                    type: 'streamlit:setComponentValue',
                    key: 'momwatch_session',
                    value: data
                }, '*');
            } catch (e) {
                console.error('Failed to parse session:', e);
            }
        }
    </script>
    """

def restore_session_if_exists():
    """Check localStorage and restore session if it exists"""
    import json
    
    # Return JS component that reads localStorage
    session_data = components.html(
        """
        <script>
            const session = localStorage.getItem('momwatch_session');
            if (session) {
                // Send session data back to Streamlit
                const data = JSON.parse(session);
                const div = document.createElement('div');
                div.id = 'session-data';
                div.style.display = 'none';
                div.textContent = session;
                document.body.appendChild(div);
            }
        </script>
        <div id="result"></div>
        """,
        height=0,
    )
    
    return session_data
