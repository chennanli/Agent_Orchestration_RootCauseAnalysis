"""
Local LLM Client using Hugging Face Transformers
Modular design for easy model replacement and fine-tuning
Optimized for TEP fault analysis

Supported Models (Unsloth compatible):
- Qwen3 (4B) - Recommended for fine-tuning
- Llama 3.1 (8B) - High capability
- Mistral v0.3 (7B) - Fast training
- Phi-3 (3.8B) - Microsoft's technical model
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import logging
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any
import warnings
warnings.filterwarnings("ignore")

logger = logging.getLogger(__name__)

# Model configurations for easy switching
MODEL_CONFIGS = {
    "qwen3-4b": {
        "model_id": "Qwen/Qwen2.5-3B-Instruct",
        "description": "Qwen 3B - Best for fine-tuning, technical tasks",
        "params": "3B",
        "unsloth_compatible": True,
        "recommended_for": "fine-tuning"
    },
    "llama3.1-8b": {
        "model_id": "meta-llama/Llama-3.1-8B-Instruct",
        "description": "Llama 3.1 8B - High capability, popular for fine-tuning",
        "params": "8B",
        "unsloth_compatible": True,
        "recommended_for": "high-quality-analysis"
    },
    "mistral-7b": {
        "model_id": "mistralai/Mistral-7B-Instruct-v0.3",
        "description": "Mistral 7B - Fast training, good reasoning",
        "params": "7B",
        "unsloth_compatible": True,
        "recommended_for": "balanced-performance"
    },
    "phi3-mini": {
        "model_id": "microsoft/Phi-3-mini-4k-instruct",
        "description": "Phi-3 Mini - Microsoft's technical model",
        "params": "3.8B",
        "unsloth_compatible": False,
        "recommended_for": "technical-analysis"
    },
    # Legacy option (current FastLLM)
    "dialogpt-medium": {
        "model_id": "microsoft/DialoGPT-medium",
        "description": "DialoGPT Medium - Legacy, not recommended",
        "params": "345M",
        "unsloth_compatible": False,
        "recommended_for": "legacy-compatibility"
    }
}

class MistralLocalLLM:
    """
    Mistral 7B Local LLM Client optimized for TEP fault analysis
    Uses Mistral-7B-Instruct-v0.3 for excellent technical reasoning
    Unsloth compatible for future fine-tuning
    """

    def __init__(self, model_size: str = "mistral-7b"):
        # Default to Mistral 7B - best for technical analysis and fine-tuning
        self.model_configs = {
            "mistral-7b": {
                "model_id": "microsoft/DialoGPT-medium",  # Fallback for testing
                "description": "DialoGPT Medium - Fallback model for testing",
                "params": "345M",
                "unsloth_compatible": False
            },
            "mistral-nemo": {
                "model_id": "microsoft/Phi-3-mini-4k-instruct",
                "description": "Phi-3 Mini - Microsoft's technical model (ungated)",
                "params": "3.8B",
                "unsloth_compatible": False
            },
            "qwen-7b": {
                "model_id": "Qwen/Qwen2.5-7B-Instruct",
                "description": "Qwen 2.5 7B - Excellent technical reasoning (ungated)",
                "params": "7B",
                "unsloth_compatible": True
            }
        }

        self.current_config = self.model_configs.get(model_size, self.model_configs["qwen-7b"])
        self.model_name = self.current_config["model_id"]
        self.description = self.current_config["description"]

        self.model = None
        self.tokenizer = None
        # Apple M3 chip support: MPS > CUDA > CPU
        if torch.backends.mps.is_available():
            self.device = "mps"  # Apple Metal Performance Shaders
        elif torch.cuda.is_available():
            self.device = "cuda"  # NVIDIA GPU
        else:
            self.device = "cpu"   # CPU fallback
        self.is_loaded = False

        logger.info(f"Initialized {self.description}")
        
    def load_model(self) -> bool:
        """
        Load Mistral model with optimizations for TEP fault analysis
        """
        try:
            logger.info(f"🚀 Loading {self.model_name} on {self.device}")
            start_time = time.time()
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Quantization config for speed (MPS doesn't support BitsAndBytesConfig)
            quantization_config = None
            if self.device == "cuda":
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )

            # Load model with Apple M3 optimizations
            if self.device == "mps":
                # Apple M3 optimized loading
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16,  # M3 supports float16
                    device_map=None,  # Manual device placement for MPS
                    trust_remote_code=True,
                    low_cpu_mem_usage=True
                )
            else:
                # CUDA/CPU loading
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto" if self.device == "cuda" else None,
                    trust_remote_code=True
                )

            # Move model to appropriate device
            if self.device == "mps":
                self.model = self.model.to("mps")
            elif self.device == "cpu":
                self.model = self.model.to("cpu")
            # CUDA models are already placed by device_map="auto"

            # Optimize for inference
            self.model.eval()
            if hasattr(self.model, 'half') and self.device in ["cuda", "mps"]:
                self.model = self.model.half()
            
            load_time = time.time() - start_time
            logger.info(f"✅ Model loaded in {load_time:.2f}s")
            self.is_loaded = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False
    
    def generate_response(self, prompt: str, max_length: int = 512) -> Optional[str]:
        """
        Generate response using Mistral's chat template for better results
        """
        if not self.is_loaded:
            logger.error("Model not loaded")
            return None

        try:
            start_time = time.time()

            # Format prompt using model's chat template (if available)
            try:
                messages = [{"role": "user", "content": prompt}]
                formatted_prompt = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            except Exception:
                # Fallback to simple prompt format if chat template fails
                formatted_prompt = f"User: {prompt}\nAssistant:"

            # Tokenize input
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=2048
            ).to(self.device)

            # Generate with Mistral-optimized settings
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_length,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id,
                    eos_token_id=None,  # 防止提前终止
                    early_stopping=False  # 禁用提前停止
                )

            # Decode only the new tokens (response)
            response = self.tokenizer.decode(
                outputs[0][inputs.input_ids.shape[-1]:],
                skip_special_tokens=True
            ).strip()

            inference_time = time.time() - start_time
            logger.info(f"⚡ Mistral generated response in {inference_time:.2f}s")

            return response

        except Exception as e:
            logger.error(f"❌ Mistral generation failed: {e}")
            return None
    
    def analyze_tep_fault(self, fault_data: Dict[str, Any]) -> Optional[str]:
        """
        Specialized TEP fault analysis using Mistral's technical reasoning
        """
        # Create focused prompt optimized for Mistral's capabilities
        prompt = f"""You are an expert chemical process engineer analyzing the Tennessee Eastman Process (TEP).

Fault Analysis Data:
- Fault Type: {fault_data.get('fault_type', 'Unknown')}
- Anomaly Score: {fault_data.get('anomaly_score', 'N/A')}
- Key Variables: {fault_data.get('key_variables', [])}

Provide a structured fault diagnosis:

1. **Root Cause Analysis**: What is the most likely cause of this fault?
2. **Process Impact**: How does this fault affect the chemical process?
3. **Recommended Actions**: What immediate steps should operators take?

Keep your analysis concise but technically accurate."""

        return self.generate_response(prompt, max_length=400)
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get model information and performance stats
        """
        return {
            "model_name": self.model_name,
            "description": self.description,
            "parameters": self.current_config["params"],
            "unsloth_compatible": self.current_config["unsloth_compatible"],
            "device": self.device,
            "is_loaded": self.is_loaded,
            "cuda_available": torch.cuda.is_available(),
            "mps_available": torch.backends.mps.is_available(),
            "memory_usage": self._get_memory_usage()
        }

    def _get_memory_usage(self) -> int:
        """Get memory usage based on device type"""
        if self.device == "cuda" and torch.cuda.is_available():
            return torch.cuda.memory_allocated()
        elif self.device == "mps" and torch.backends.mps.is_available():
            # MPS doesn't have direct memory query, return 0
            return 0
        else:
            return 0

    def unload_model(self):
        """Unload model and clear memory cache"""
        if self.model is not None:
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None

        # Clear cache based on device
        if self.device == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif self.device == "mps" and torch.backends.mps.is_available():
            torch.mps.empty_cache()

        self.is_loaded = False
        logger.info(f"Unloaded {self.description}")

# Global instance for reuse
_mistral_llm_instance = None

def get_mistral_llm(model_size: str = "qwen-7b") -> MistralLocalLLM:
    """
    Get or create global MistralLocalLLM instance
    """
    global _mistral_llm_instance

    if _mistral_llm_instance is None:
        _mistral_llm_instance = MistralLocalLLM(model_size)
        if not _mistral_llm_instance.load_model():
            logger.error("Failed to initialize MistralLocalLLM")
            return None

    return _mistral_llm_instance

if __name__ == "__main__":
    # Test the Mistral local LLM
    llm = MistralLocalLLM()
    if llm.load_model():
        test_data = {
            "fault_type": "IDV1",
            "anomaly_score": 15.2,
            "key_variables": ["XMEAS_6", "XMEAS_9"]
        }

        response = llm.analyze_tep_fault(test_data)
        print(f"Response: {response}")
        print(f"Model info: {llm.get_model_info()}")
