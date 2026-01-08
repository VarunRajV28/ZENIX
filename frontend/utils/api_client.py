"""
Backend API Client
HTTP client for communicating with FastAPI backend
"""

import requests
import streamlit as st
from typing import Dict, List, Optional
import time
from functools import wraps

# Backend API base URL
API_BASE_URL = "http://backend:8000"  # Docker internal network
# For local development: API_BASE_URL = "http://localhost:8000"

def retry_on_failure(max_attempts=3, delay=1):
    """Decorator for retrying API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

class BackendAPIClient:
    """HTTP client for backend API with error handling"""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url
        self.timeout = 10
    
    def _get_headers(self, token: Optional[str] = None) -> Dict:
        """Build request headers with optional JWT token"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    @retry_on_failure(max_attempts=3)
    def register(self, email: str, password: str, full_name: str, role: str, **kwargs) -> Dict:
        """Register new user account"""
        payload = {
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
            **kwargs
        }
        
        response = requests.post(
            f"{self.base_url}/auth/register",
            json=payload,
            headers=self._get_headers(),
            timeout=self.timeout
        )
        
        if response.status_code == 422:
            error_detail = response.json().get('detail', 'Validation error')
            raise ValueError(f"Invalid input: {error_detail}")
        elif response.status_code == 400:
            raise ValueError(response.json().get('detail', 'Registration failed'))
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def login(self, email: str, password: str) -> Dict:
        """Authenticate user and retrieve JWT token"""
        payload = {
            "username": email,  # OAuth2 uses 'username' field
            "password": password
        }
        
        response = requests.post(
            f"{self.base_url}/auth/login",
            data=payload,  # Form data for OAuth2
            timeout=self.timeout
        )
        
        if response.status_code == 401:
            raise ValueError("Invalid email or password")
        elif response.status_code == 422:
            raise ValueError("Invalid credentials format")
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def submit_triage(self, vitals: Dict, token: str, idempotency_key: str) -> Dict:
        """Submit triage assessment with idempotency key"""
        headers = self._get_headers(token)
        headers["x-idempotency-key"] = idempotency_key
        
        # Separate notes from vitals if present
        notes = vitals.pop("symptoms", None)
        
        # Wrap vitals in the expected format
        payload = {
            "vitals": vitals
        }
        if notes:
            payload["notes"] = notes
        
        response = requests.post(
            f"{self.base_url}/triage",
            json=payload,
            headers=headers,
            timeout=30  # Longer timeout for ML inference
        )
        
        if response.status_code == 422:
            error_detail = response.json().get('detail', [])
            if isinstance(error_detail, list) and len(error_detail) > 0:
                field_errors = [f"{err['loc'][-1]}: {err['msg']}" for err in error_detail]
                raise ValueError("Validation errors:\n" + "\n".join(field_errors))
            raise ValueError(f"Invalid vitals data: {error_detail}")
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def get_emergency_feed(self, token: str) -> List[Dict]:
        """Fetch CRITICAL patients (doctor only)"""
        response = requests.get(
            f"{self.base_url}/doctor/dashboard/emergency",
            headers=self._get_headers(token),
            timeout=self.timeout
        )
        
        if response.status_code == 403:
            raise PermissionError("Doctor access required")
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def get_priority_patients(self, token: str) -> List[Dict]:
        """Fetch priority-sorted patient list (doctor only)"""
        response = requests.get(
            f"{self.base_url}/doctor/patients/priority",
            headers=self._get_headers(token),
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def get_patient_details(self, patient_id: str, token: str) -> Dict:
        """Fetch detailed patient history (doctor only)"""
        response = requests.get(
            f"{self.base_url}/doctor/patients/{patient_id}/details",
            headers=self._get_headers(token),
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def get_profile(self, token: str) -> Dict:
        """Fetch mother's profile"""
        response = requests.get(
            f"{self.base_url}/mother/profile",
            headers=self._get_headers(token),
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def update_profile(self, profile_data: Dict, token: str) -> Dict:
        """Update mother's profile"""
        response = requests.put(
            f"{self.base_url}/mother/profile",
            json=profile_data,
            headers=self._get_headers(token),
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def get_history(self, token: str) -> List[Dict]:
        """Fetch mother's triage history"""
        response = requests.get(
            f"{self.base_url}/mother/history",
            headers=self._get_headers(token),
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=3)
    def get_health_passport(self, token: str) -> Dict:
        """Generate health passport report"""
        response = requests.get(
            f"{self.base_url}/mother/health-passport",
            headers=self._get_headers(token),
            timeout=self.timeout
        )
        
        response.raise_for_status()
        return response.json()
    
    @retry_on_failure(max_attempts=2)
    def get_system_health(self, token: str) -> Dict:
        """Get system health status (admin)"""
        response = requests.get(
            f"{self.base_url}/admin/system/health",
            headers=self._get_headers(token),
            timeout=5
        )
        
        response.raise_for_status()
        return response.json()


# Singleton instance
api_client = BackendAPIClient()
