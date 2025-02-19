import requests
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class StraikerError(Exception):
    """Base exception for Straiker SDK errors"""
    pass

class NetworkInfo:
    """Helper class to structure network information"""
    def __init__(
        self,
        ip: str,
        user_agent: str,
        referer: str = "",
        additional_headers: Dict[str, str] = None
    ):
        self.ip = ip
        self.user_agent = user_agent
        self.referer = referer
        self.additional_headers = additional_headers or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to API-compatible dictionary"""
        return {
            "ip": self.ip,
            "user_agent": self.user_agent,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept_language": "en-US,en;q=0.9",
            "accept_encoding": "gzip, deflate, br, zstd",
            "content_type": "application/json",
            "content_length": "100",
            "cache_control": "max-age=0",
            "connection": "keep-alive",
            "referer": self.referer,
            "sec_ch_ua": "Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24",
            "sec_ch_ua_platform": "macOS",
            "additional_headers": self.additional_headers
        }

class DetectionCategory(Enum):
    """Categories of security detections"""
    PII = "pii"
    SAFETY = "safety"
    SECRET = "secret"
    LLM_EVASION = "llm_evasion"
    SESSION = "session"

class DetectionType(Enum):
    """Types of detections within categories"""
    INPUT = "input"
    OUTPUT = "output"
    SESSION = "session"

@dataclass
class DetectionResult:
    """Structured response from Straiker API"""
    turn_id: str
    score: float
    blocking_score: float
    monitoring_score: float
    detections: Dict[str, Dict[str, float]]
    disabled_checks: List[str]

    def get_detections_by_category(self, category: DetectionCategory) -> Dict[str, float]:
        """Get all detections for a specific category (e.g., 'pii', 'safety')"""
        results = {}
        for detection_type in self.detections.values():
            for check, score in detection_type.items():
                if f":{category.value}:" in check:
                    results[check] = score
        return results

    def get_detections_by_type(self, type: DetectionType) -> Dict[str, float]:
        """Get all detections for a specific type (input/output)"""
        results = {}
        for detection_type in self.detections.values():
            for check, score in detection_type.items():
                if check.startswith(f"{type.value}:"):
                    results[check] = score
        return results

    def get_high_risk_detections(self, threshold: float = 0.0) -> Dict[str, float]:
        """Get all detections above a certain threshold"""
        results = {}
        for detection_type in self.detections.values():
            for check, score in detection_type.items():
                if score > threshold:
                    results[check] = score
        return results

    def summarize_detections(self) -> str:
        """Get a human-readable summary of detections"""
        summary = []
        
        # Add overall scores
        summary.append(f"Overall Risk Score: {self.score}")
        summary.append(f"Blocking Risk: {self.blocking_score}")
        summary.append(f"Monitoring Risk: {self.monitoring_score}")
        
        # Add high-risk detections
        high_risk = self.get_high_risk_detections(0.0)
        if high_risk:
            summary.append("\nDetected Issues:")
            for check, score in high_risk.items():
                # Parse the check name for better readability
                parts = check.split(":")
                type_str = parts[0].capitalize()
                category = parts[1].upper()
#                detail = parts[1].replace("_", " ").capitalize()
                summary.append(f"- {type_str} {category}: {score}")
        
        # Add disabled checks if any
        if self.disabled_checks:
            summary.append("\nDisabled Checks:")
            for check in self.disabled_checks:
                summary.append(f"- {check}")
        
        return "\n".join(summary)

    @classmethod
    def from_response(cls, response_data: Dict[str, Any]) -> 'DetectionResult':
        """Create DetectionResult instance from API response"""
        debug = response_data.get('debug', {})
        detections = debug.get('detections', {})
        return cls(
            turn_id=response_data.get('turn_id', ''),
            score=response_data.get('score', 0.0),
            blocking_score=debug.get('score_blocking', 0.0),
            monitoring_score=debug.get('score_detect', 0.0),
            detections={
                'blocking': detections.get('block', {}),
                'monitoring': detections.get('detect', {})
            },
            disabled_checks=detections.get('disabled', [])
        )

class Straiker:
    """Main SDK class for interacting with Straiker API"""
    
    def __init__(
        self,
        api_key: str,
        user_name: str = "Straiker SDK",
        base_url: str = "https://defend.dev.straiker.ai",
        debug: bool = False
    ):
        self.api_key = api_key
        self.user_name = user_name
        self.base_url = base_url.rstrip('/')
        self.debug = debug

    def _get_headers(self) -> Dict[str, str]:
        """Generate headers for API requests"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        if self.debug:
            headers['Straiker-Debug'] = 'true'
        return headers

    def detect(
        self,
        prompt: str,
        app_response: str,
        user_name: str = None,  # Made optional since it can come from init
        user_role: str = "public",
        session_id: str = "",
        rag_content: str = "",
        network_info: Optional[NetworkInfo] = None,
        annotations: Optional[Dict[str, str]] = None
    ) -> DetectionResult:
        """Send a detection request to Straiker API"""
        # Start with base payload
        payload = {
            "user_name": user_name or self.user_name,  # Use provided user_name or fall back to init value
            "user_role": user_role,
            "session_id": session_id,
            "prompt": prompt,
            "rag_content": rag_content,
            "app_response": app_response,
            "annotations": annotations or {},
            "network": {
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "accept_encoding": "gzip, deflate, br, zstd",
                "accept_language": "en-US,en;q=0.9",
                "additional_headers": {
                    "sec-ch-ua-mobile": "?0"
                },
                "cache_control": "max-age=0",
                "connection": "keep-alive",
                "content_length": "100",
                "content_type": "application/json",
                "ip": "127.0.0.1",
                "referer": "https://chat.labs.straiker.ai/",
                "sec_ch_ua": "Google Chrome\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24",
                "sec_ch_ua_platform": "macOS",
                "user_agent": "Saige/1.0"
            }
        }

        # Override with provided network info if available
        if network_info:
            network_dict = network_info.to_dict()
            payload["network"].update(network_dict)

        try:
            # Ensure proper JSON formatting with double quotes
            json_payload = json.dumps(payload, ensure_ascii=False)
            
            response = requests.post(
                f"{self.base_url}/api/v1/detect",
                headers=self._get_headers(),
                data=json_payload
            )
            response.raise_for_status()
            return DetectionResult.from_response(response.json())
            
        except requests.exceptions.RequestException as e:
            raise StraikerError(f"API request failed: {str(e)}") from e
        except (KeyError, json.JSONDecodeError) as e:
            raise StraikerError(f"Invalid API response: {str(e)}") from e 