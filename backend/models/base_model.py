"""
Abstract Base Class for Local LLM Models
Provides consistent interface for all model implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import torch
import logging

logger = logging.getLogger(__name__)

class BaseLocalLLM(ABC):
    """
    Abstract base class for local LLM implementations
    Ensures consistent interface across different models
    """
    
    def __init__(self, model_config: Dict[str, Any]):
        self.model_config = model_config
        self.model_id = model_config["model_id"]
        self.description = model_config["description"]
        self.params = model_config["params"]
        self.unsloth_compatible = model_config.get("unsloth_compatible", False)
        
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.is_loaded = False
        
        logger.info(f"Initializing {self.description}")
    
    @abstractmethod
    def load_model(self) -> bool:
        """Load the model and tokenizer"""
        pass
    
    @abstractmethod
    def generate_response(self, prompt: str, max_length: int = 512) -> Optional[str]:
        """Generate response from prompt"""
        pass
    
    def analyze_tep_fault(self, fault_data: Dict[str, Any]) -> Optional[str]:
        """
        Specialized TEP fault analysis with optimized prompt
        Can be overridden by specific model implementations
        """
        # Create focused prompt for TEP analysis
        prompt = f"""
TEP Fault Analysis:
Fault Type: {fault_data.get('fault_type', 'Unknown')}
Anomaly Score: {fault_data.get('anomaly_score', 'N/A')}
Key Variables: {fault_data.get('key_variables', [])}

Provide a concise fault diagnosis:
1. Root cause
2. Impact on process  
3. Recommended action

Analysis:"""
        
        return self.generate_response(prompt, max_length=256)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and performance stats"""
        return {
            "model_id": self.model_id,
            "description": self.description,
            "parameters": self.params,
            "device": self.device,
            "is_loaded": self.is_loaded,
            "unsloth_compatible": self.unsloth_compatible,
            "cuda_available": torch.cuda.is_available(),
            "memory_usage": torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        }
    
    def unload_model(self):
        """Unload model to free memory"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer  
            self.tokenizer = None
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.is_loaded = False
        logger.info(f"Unloaded {self.description}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.unload_model()
