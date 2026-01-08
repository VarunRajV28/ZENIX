"""
Zudu AI Integration - Advanced Maternal Health NLP Insights
============================================================
Integrates with Zudu AI API for enhanced clinical decision support,
NLP-powered risk explanations, and personalized recommendations.

Features:
- Async HTTP requests with timeout and retry logic
- Exponential backoff for failed requests
- Graceful fallback if API unavailable
- Non-blocking integration (doesn't fail main triage flow)

Error Handling:
- Returns fallback response if API fails
- Logs all failures for monitoring
- Tracks API availability metrics
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from app.engine.sanity import ClinicalVitals
from app.engine.rules import ClinicalAlert
from app.config import settings
from app.utils.logger import logger


class ZuduAPIException(Exception):
    """Custom exception for Zudu AI API failures."""
    pass


class ZuduAIClient:
    """
    Zudu AI API client for maternal health insights.
    """
    
    def __init__(self):
        self.api_key = settings.ZUDU_API_KEY
        self.endpoint = settings.ZUDU_API_ENDPOINT
        self.timeout = settings.ZUDU_TIMEOUT_SECONDS
        self.max_retries = settings.ZUDU_MAX_RETRIES
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create aiohttp session.
        """
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self) -> None:
        """
        Close aiohttp session.
        """
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _make_request(
        self,
        payload: Dict[str, Any],
        attempt: int = 1
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Zudu AI API with retry logic.
        
        Args:
            payload: JSON payload
            attempt: Current attempt number
        
        Returns:
            API response data
        
        Raises:
            ZuduAPIException: If all retry attempts fail
        """
        session = await self._get_session()
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            logger.debug(f"Zudu AI request attempt {attempt}/{self.max_retries}")
            
            async with session.post(
                self.endpoint,
                json=payload,
                headers=headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("✓ Zudu AI API call successful")
                    return data
                
                elif response.status == 401:
                    logger.error("Zudu AI authentication failed: Invalid API key")
                    raise ZuduAPIException("Invalid Zudu AI API key")
                
                elif response.status == 429:
                    logger.warning("Zudu AI rate limit exceeded")
                    raise ZuduAPIException("Rate limit exceeded")
                
                else:
                    error_text = await response.text()
                    logger.warning(f"Zudu AI error {response.status}: {error_text}")
                    raise ZuduAPIException(f"API error {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            logger.warning(f"Zudu AI request timeout (attempt {attempt})")
            if attempt < self.max_retries:
                # Exponential backoff
                sleep_time = 2 ** attempt
                await asyncio.sleep(sleep_time)
                return await self._make_request(payload, attempt + 1)
            raise ZuduAPIException("Request timeout after retries")
        
        except aiohttp.ClientError as e:
            logger.warning(f"Zudu AI connection error: {str(e)}")
            if attempt < self.max_retries:
                sleep_time = 2 ** attempt
                await asyncio.sleep(sleep_time)
                return await self._make_request(payload, attempt + 1)
            raise ZuduAPIException(f"Connection error: {str(e)}")
    
    async def analyze_clinical_context(
        self,
        vitals: ClinicalVitals,
        risk_assessment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze clinical context and get AI-powered insights.
        
        Args:
            vitals: Patient vital signs
            risk_assessment: Current risk assessment from rules/ML
        
        Returns:
            Dictionary with clinical insights, recommendations, and explanations
        """
        if not self.api_key or self.api_key == "your_zudu_api_key_here":
            logger.warning("Zudu AI API key not configured, using fallback")
            return self._get_fallback_response("API key not configured")
        
        try:
            payload = {
                "vitals": {
                    "age": vitals.age,
                    "systolic_bp": vitals.systolic_bp,
                    "diastolic_bp": vitals.diastolic_bp,
                    "blood_sugar": vitals.blood_sugar,
                    "body_temp": vitals.body_temp,
                    "heart_rate": vitals.heart_rate,
                    "blood_oxygen": vitals.blood_oxygen,
                    "gestational_weeks": vitals.gestational_weeks
                },
                "current_risk": risk_assessment.get("risk_level", "UNKNOWN"),
                "alerts": risk_assessment.get("alerts", []),
                "patient_age": vitals.age,
                "gestational_weeks": vitals.gestational_weeks
            }
            
            # Make API request with timeout
            response = await self._make_request(payload)
            
            return {
                "clinical_insights": response.get(
                    "clinical_insights",
                    "AI analysis completed"
                ),
                "recommended_actions": response.get("recommended_actions", []),
                "risk_explanation": response.get(
                    "risk_explanation",
                    "Risk factors analyzed"
                ),
                "urgency_score": response.get("urgency_score", 5.0),
                "zudu_available": True
            }
        
        except ZuduAPIException as e:
            logger.warning(f"Zudu AI unavailable: {str(e)}")
            return self._get_fallback_response(str(e))
        
        except Exception as e:
            logger.error(f"Unexpected Zudu AI error: {str(e)}", exc_info=True)
            return self._get_fallback_response("Unexpected error")
    
    async def get_recommendations(
        self,
        patient_history: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Get personalized recommendations based on patient history.
        
        Args:
            patient_history: List of previous triage assessments
        
        Returns:
            List of recommendation strings
        """
        if not self.api_key or self.api_key == "your_zudu_api_key_here":
            return ["Complete medical evaluation with healthcare provider"]
        
        try:
            payload = {
                "patient_history": patient_history[-10:],  # Last 10 assessments
                "request_type": "recommendations"
            }
            
            response = await self._make_request(payload)
            return response.get("recommendations", [
                "Continue routine prenatal care",
                "Monitor vital signs regularly"
            ])
        
        except Exception as e:
            logger.warning(f"Failed to get Zudu recommendations: {str(e)}")
            return ["Continue routine prenatal care"]
    
    async def explain_risk_factors(
        self,
        alerts: List[str]
    ) -> str:
        """
        Get detailed explanation of risk factors.
        
        Args:
            alerts: List of clinical alerts
        
        Returns:
            Detailed explanation string
        """
        if not self.api_key or self.api_key == "your_zudu_api_key_here":
            return "Consult healthcare provider for detailed risk assessment"
        
        try:
            payload = {
                "alerts": alerts,
                "request_type": "explanation"
            }
            
            response = await self._make_request(payload)
            return response.get(
                "explanation",
                "Risk factors require medical evaluation"
            )
        
        except Exception as e:
            logger.warning(f"Failed to get Zudu explanation: {str(e)}")
            return "Consult healthcare provider for detailed risk assessment"
    
    def _get_fallback_response(self, reason: str) -> Dict[str, Any]:
        """
        Get fallback response when Zudu AI unavailable.
        
        Args:
            reason: Reason for fallback
        
        Returns:
            Fallback response dictionary
        """
        return {
            "clinical_insights": f"Zudu AI unavailable ({reason}). Using clinical rules assessment.",
            "recommended_actions": [
                "Consult with healthcare provider for detailed evaluation",
                "Continue monitoring vital signs regularly",
                "Follow prescribed prenatal care schedule"
            ],
            "risk_explanation": "Standard clinical assessment completed. Consult healthcare provider for AI-enhanced insights.",
            "urgency_score": 5.0,
            "zudu_available": False
        }


# Global Zudu AI client instance
zudu_client = ZuduAIClient()
