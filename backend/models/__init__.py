"""
Local LLM Models Package
Modular structure for easy model management and fine-tuning

Directory Structure:
- models/
  - __init__.py (this file)
  - base_model.py (abstract base class)
  - qwen3_model.py (Qwen3 4B implementation)
  - llama_model.py (Llama 3.1 8B implementation) 
  - mistral_model.py (Mistral 7B implementation)
  - model_factory.py (factory for creating models)
  - fine_tuned/ (directory for fine-tuned models)
  - cache/ (model cache directory)

Usage:
    from models import ModelFactory
    model = ModelFactory.create_model("qwen3-4b")
    response = model.generate("Analyze this fault...")
"""

from .model_factory import ModelFactory
from .base_model import BaseLocalLLM

__all__ = ["ModelFactory", "BaseLocalLLM"]
