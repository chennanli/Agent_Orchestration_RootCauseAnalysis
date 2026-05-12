"""
Simplified Multi-LLM Client for FaultExplainer
Only supports LMStudio (local) and Claude (API)
Gemini removed for performance
"""

import json
import requests
from anthropic import Anthropic
from openai import OpenAI
from typing import Dict, List, Any, Optional
import asyncio
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import os

logger = logging.getLogger(__name__)

def resolve_env_vars(value: str) -> str:
    """Resolve environment variables in config values like ${VAR_NAME}"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, value)
    return value


class MultiLLMClient:
    """Simplified Multi-LLM client supporting only LMStudio and Claude"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clients = {}
        self.enabled_models = []
        self.runtime_enabled_models = set()
        self.usage_stats = defaultdict(int)
        self.cost_tracking = defaultdict(float)
        
        # Premium session management
        self.premium_session_start = None
        self.premium_session_duration_minutes = config.get("cost_protection", {}).get("premium_session_duration_minutes", 30)
        self.session_timer = None
        
        # Initialize only LMStudio and Claude
        for model_name, model_config in config["models"].items():
            if model_name == "lmstudio":
                self.clients[model_name] = self._init_lmstudio(model_config)
                if model_config.get("enabled", False):
                    self.enabled_models.append(model_name)
            elif model_name == "anthropic":
                self.clients[model_name] = self._init_claude(model_config)
                if model_config.get("enabled", False):
                    self.enabled_models.append(model_name)
        
        print(f"✅ Initialized models: {list(self.clients.keys())}")
        print(f"📊 Config-enabled models: {self.enabled_models}")
    
    def _init_lmstudio(self, config: Dict[str, Any]) -> OpenAI:
        """Initialize LMStudio client"""
        return OpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"]
        )
    
    def _init_claude(self, config: Dict[str, Any]) -> Anthropic:
        """Initialize Claude client"""
        api_key = resolve_env_vars(config["api_key"])
        return Anthropic(api_key=api_key)
    
    def _is_premium_model(self, model_name: str) -> bool:
        """Check if model is premium (costs money)"""
        return model_name == "anthropic"
    
    def _start_premium_session_timer(self):
        """Start auto-shutdown timer for premium models"""
        if self.premium_session_start is None:
            self.premium_session_start = datetime.now()
            print(f"⏰ Premium session started - will auto-shutdown in {self.premium_session_duration_minutes} minutes")
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get current premium session status"""
        if self.premium_session_start is None:
            return {
                "premium_session_active": False,
                "remaining_time_minutes": 0
            }
        
        elapsed = (datetime.now() - self.premium_session_start).total_seconds() / 60
        remaining = max(0, self.premium_session_duration_minutes - elapsed)
        
        return {
            "premium_session_active": True,
            "elapsed_time_minutes": int(elapsed),
            "remaining_time_minutes": int(remaining),
            "auto_shutdown": remaining <= 0
        }
    
    def toggle_model(self, model_name: str, enabled: bool) -> Dict[str, Any]:
        """Toggle a model on/off at runtime"""
        try:
            if model_name not in self.clients:
                return {"error": f"Model {model_name} not available"}
            
            is_config_enabled = model_name in self.enabled_models
            
            if enabled:
                if not is_config_enabled:
                    self.runtime_enabled_models.add(model_name)
                self.runtime_enabled_models.discard(f"disabled_{model_name}")
                logger.info(f"Enabled {model_name} for runtime use")
                
                if self._is_premium_model(model_name):
                    self._start_premium_session_timer()
            else:
                if is_config_enabled:
                    self.runtime_enabled_models.add(f"disabled_{model_name}")
                else:
                    self.runtime_enabled_models.discard(model_name)
                logger.info(f"Disabled {model_name} for runtime use")
            
            return {
                "status": "success",
                "model": model_name,
                "enabled": enabled,
                "active_models": list(self.get_active_models())
            }
        except Exception as e:
            logger.error(f"Error toggling model {model_name}: {str(e)}")
            return {"error": str(e)}
    
    def get_active_models(self) -> set:
        """Get currently active models"""
        config_enabled = set(self.enabled_models)
        runtime_enabled = {m for m in self.runtime_enabled_models if not m.startswith('disabled_')}
        runtime_disabled = {m.replace('disabled_', '') for m in self.runtime_enabled_models if m.startswith('disabled_')}
        
        active = config_enabled.union(runtime_enabled)
        active = active - runtime_disabled
        
        return active
    
    def get_model_status(self) -> Dict[str, Any]:
        """Get detailed status of all models"""
        return {
            "config_enabled": list(self.enabled_models),
            "runtime_enabled": list(self.runtime_enabled_models),
            "active_models": list(self.get_active_models()),
            "available_models": list(self.clients.keys()),
            "usage_stats": dict(self.usage_stats),
            "cost_tracking": dict(self.cost_tracking)
        }
    
    async def get_analysis_from_all_models(
        self,
        system_message: str,
        user_prompt: str,
        feature_comparison: str = ""
    ) -> Dict[str, Any]:
        """Get analysis from all active models in parallel"""
        
        active_models = self.get_active_models()
        
        if not active_models:
            return {
                "error": "No models enabled",
                "results": {},
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"🚀 Starting PARALLEL analysis with {len(active_models)} models: {list(active_models)}")
        
        async def query_model(model_name: str):
            """Query a single model"""
            start_time = time.time()
            try:
                print(f"🤖 Querying {model_name}...")
                
                if model_name == "lmstudio":
                    response = await self._query_lmstudio(system_message, user_prompt)
                elif model_name == "anthropic":
                    response = await self._query_claude(system_message, user_prompt)
                else:
                    response = f"Unknown model: {model_name}"
                
                response_time = time.time() - start_time
                print(f"✅ {model_name} completed in {response_time:.2f}s")
                
                self.usage_stats[model_name] += 1
                
                return (model_name, {
                    "analysis": response,
                    "response_time": response_time,
                    "status": "success"
                })
            except Exception as e:
                response_time = time.time() - start_time
                print(f"❌ {model_name} failed: {str(e)}")
                return (model_name, {
                    "analysis": f"Error: {str(e)}",
                    "response_time": response_time,
                    "status": "error"
                })
        
        # Execute all models in parallel
        tasks = [query_model(model) for model in active_models]
        model_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        results = {}
        for result in model_results:
            if isinstance(result, Exception):
                print(f"⚠️ Model execution exception: {result}")
                continue
            model_name, model_result = result
            results[model_name] = model_result
            print(f"📊 Collected result from {model_name}: {model_result.get('status')}")
        
        print(f"🎉 PARALLEL analysis complete! {len(results)} models finished")
        
        return {
            "results": results,
            "timestamp": datetime.now().isoformat(),
            "models_queried": list(active_models)
        }
    
    async def _query_lmstudio(self, system_message: str, user_prompt: str) -> str:
        """Query LMStudio with retry logic"""
        client = self.clients["lmstudio"]
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                print(f"🤖 LMStudio attempt {attempt + 1}/{max_retries}")
                
                loop = asyncio.get_event_loop()
                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.chat.completions.create(
                            model="local-model",
                            messages=[
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=0.7,
                            max_tokens=2000
                        )
                    ),
                    timeout=300  # 5 minutes for local model
                )
                
                return response.choices[0].message.content
            
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    print(f"⏱️ LMStudio timeout, retrying...")
                    await asyncio.sleep(2)
                else:
                    raise Exception("LMStudio timeout after 3 attempts")
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ LMStudio error: {e}, retrying...")
                    await asyncio.sleep(2)
                else:
                    raise Exception(f"LMStudio failed: {str(e)}")
    
    async def _query_claude(self, system_message: str, user_prompt: str) -> str:
        """Query Claude with timeout"""
        client = self.clients["anthropic"]
        
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.messages.create(
                        model=self.config["models"]["anthropic"]["model_name"],
                        max_tokens=2000,
                        system=system_message,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                ),
                timeout=30  # 30 seconds timeout
            )
            
            return response.content[0].text
        
        except asyncio.TimeoutError:
            raise Exception("Claude timeout after 30 seconds")
        except Exception as e:
            raise Exception(f"Claude failed: {str(e)}")
    
    def format_comparative_results(self, results: Dict[str, Any], feature_comparison: str = "") -> Dict[str, Any]:
        """Format results for frontend display"""
        formatted = {
            "timestamp": datetime.now().isoformat(),
            "feature_analysis": feature_comparison,
            "llm_analyses": {},
            "performance_summary": {}
        }
        
        for model_name, result in results.get("results", {}).items():
            formatted["llm_analyses"][model_name] = {
                "analysis": result.get("analysis", ""),
                "response_time": result.get("response_time", 0),
                "status": result.get("status", "unknown")
            }
            
            formatted["performance_summary"][model_name] = {
                "response_time": result.get("response_time", 0),
                "word_count": len(result.get("analysis", "").split())
            }
        
        return formatted

