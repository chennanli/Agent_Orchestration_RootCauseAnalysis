"""
Multi-LLM Client for FaultExplainer
Supports:
- Claude (Anthropic API) - Premium, high-quality reasoning
- Gemini (Google API) - Premium with free tier, fast, 1M context
- LMStudio (local) - Free, runs on your machine
"""

import json
import requests
from anthropic import Anthropic
from openai import OpenAI
try:
    from google import genai  # type: ignore
    from google.genai import types  # type: ignore
    _GENAI_AVAILABLE = True
except Exception:  # noqa: BLE001
    genai = None  # type: ignore
    types = None  # type: ignore
    _GENAI_AVAILABLE = False
from typing import Dict, List, Any, Optional
import asyncio
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import os
from dotenv import load_dotenv

# 🔧 CRITICAL FIX: Load .env file to get API keys
load_dotenv()

logger = logging.getLogger(__name__)

def resolve_env_vars(value: str) -> str:
    """Resolve environment variables in config values like ${VAR_NAME}"""
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        env_var = value[2:-1]
        return os.getenv(env_var, value)
    return value


class MultiLLMClient:
    """Multi-LLM client supporting Claude, Gemini, and LMStudio"""

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

        # Shutdown callback for simulation control
        self.shutdown_callback = None

        # Initialize Claude, Gemini, and LMStudio
        for model_name, model_config in config["models"].items():
            if model_name == "lmstudio":
                self.clients[model_name] = self._init_lmstudio(model_config)
                if model_config.get("enabled", False):
                    self.enabled_models.append(model_name)
            elif model_name == "anthropic":
                self.clients[model_name] = self._init_claude(model_config)
                if model_config.get("enabled", False):
                    self.enabled_models.append(model_name)
            elif model_name == "gemini":
                self.clients[model_name] = self._init_gemini(model_config)
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

    def _init_gemini(self, config: Dict[str, Any]) -> Optional[dict]:
        """Initialize Gemini client - returns dict with client and model name.

        Returns None (and logs a warning) when the optional `google-genai`
        SDK is not installed; the rest of the system continues to work via
        the Claude / LMStudio / NIM paths.
        """
        if not _GENAI_AVAILABLE:
            logger.warning(
                "google-genai not installed; skipping Gemini client init"
            )
            return None

        api_key = resolve_env_vars(config["api_key"])
        model_name = config.get("model_name", "gemini-2.5-flash")

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=180_000),
        )

        return {
            "client": client,
            "model_name": model_name,
        }

    def _is_premium_model(self, model_name: str) -> bool:
        """Check if model is premium (costs money)"""
        return model_name in ["anthropic", "gemini"]  # lmstudio is free
    
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

    def register_shutdown_callback(self, callback):
        """Register a callback to be called when premium session expires"""
        self.shutdown_callback = callback
        logger.info("Shutdown callback registered")

    def trigger_shutdown_if_expired(self):
        """Check if premium session expired and trigger shutdown if needed"""
        status = self.get_session_status()
        if status.get("auto_shutdown") and self.shutdown_callback:
            logger.warning("Premium session expired - triggering shutdown")
            self.shutdown_callback()
            return True
        return False
    
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
        """
        Get currently active models - respects both config.json AND runtime toggles

        Returns models that are:
        - Enabled in config.json AND not runtime-disabled
        - OR runtime-enabled (even if not in config)
        """
        # Start with config-enabled models
        config_enabled = set(self.enabled_models)

        # Apply runtime toggles
        # Remove models that were runtime-disabled
        for model_name in config_enabled.copy():
            if f"disabled_{model_name}" in self.runtime_enabled_models:
                config_enabled.discard(model_name)

        # Add models that were runtime-enabled (even if not in config)
        for item in self.runtime_enabled_models:
            if not item.startswith("disabled_"):
                config_enabled.add(item)

        print(f"🔍 Active models: {config_enabled}")
        print(f"📊 Config-enabled: {self.enabled_models}")
        print(f"⚙️ Runtime toggles: {self.runtime_enabled_models}")

        return config_enabled
    
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
        feature_comparison: str = "",
        fault_features: list = None,
        fault_data: dict = None
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
                elif model_name == "gemini":
                    response = await self._query_gemini(system_message, user_prompt)
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
        max_retries = 1  # 🔧 REDUCED: Fail fast instead of waiting 3x timeout (was 3)

        # 🔧 NEW: Auto-detect loaded model from LMStudio
        loaded_model = None
        try:
            models_response = client.models.list()
            if models_response.data and len(models_response.data) > 0:
                loaded_model = models_response.data[0].id
                print(f"✅ Auto-detected LMStudio model: {loaded_model}")
            else:
                print(f"⚠️ No models loaded in LMStudio, using fallback")
                loaded_model = "local-model"  # Fallback
        except Exception as e:
            print(f"⚠️ Failed to detect LMStudio model: {e}, using fallback")
            loaded_model = "local-model"  # Fallback

        # 🔧 NEW: Shorten prompts for LMStudio to fit 4096 token context limit
        # phi3-mini has 4096 token limit, need to reduce prompt from ~3500 to ~2000 tokens
        shortened_system = "You are analyzing TEP process faults. Identify root causes from the feature analysis."
        shortened_user = user_prompt

        # Try to extract just the essential parts if prompt is too long
        if len(user_prompt) > 1500:  # Roughly 375 tokens at 4 chars/token
            print(f"⚠️ User prompt too long ({len(user_prompt)} chars), shortening for LMStudio...")
            # Extract just the feature analysis part
            if "Top 6 Contributing Features" in user_prompt:
                feature_start = user_prompt.find("Top 6 Contributing Features")
                feature_section = user_prompt[feature_start:feature_start+1000]  # Take first 1000 chars
                shortened_user = f"Analyze this fault:\n\n{feature_section}\n\nProvide root cause analysis."
                print(f"   Shortened to {len(shortened_user)} chars")

        print(f"📝 LMStudio prompts: system={len(shortened_system)} chars, user={len(shortened_user)} chars")

        for attempt in range(max_retries):
            try:
                import time
                attempt_start = time.time()
                print(f"🤖 LMStudio attempt {attempt + 1}/{max_retries} at {time.strftime('%H:%M:%S')}")
                print(f"📤 Sending request to LMStudio (http://127.0.0.1:1234)...")

                loop = asyncio.get_event_loop()

                # 🔧 NEW: Add pre-request logging
                print(f"🔧 Creating chat completion request...")
                print(f"   - Model: {loaded_model}")
                print(f"   - System message length: {len(shortened_system)} chars")
                print(f"   - User prompt length: {len(shortened_user)} chars")
                print(f"   - Timeout: 45 seconds")  # 🔧 REDUCED: Model should already be loaded

                response = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: client.chat.completions.create(
                            model=loaded_model,  # 🔧 FIX: Use auto-detected model name
                            messages=[
                                {"role": "system", "content": shortened_system},  # 🔧 FIXED: Use shortened prompts
                                {"role": "user", "content": shortened_user}  # 🔧 FIXED: Use shortened prompts
                            ],
                            temperature=0.7,
                            max_tokens=2000,
                            stream=False  # 🔧 FIX: Explicitly disable streaming
                        )
                    ),
                    timeout=45  # 🔧 REDUCED: 45 seconds (model should be loaded already, was 600s)
                )

                request_duration = time.time() - attempt_start
                print(f"📥 Received response from LMStudio in {request_duration:.2f}s")

                # 🔧 FIX: Add response validation
                if not response or not response.choices:
                    print(f"❌ LMStudio response structure invalid: {response}")
                    raise Exception("LMStudio returned empty response")

                message = response.choices[0].message
                content = message.content or ""
                reasoning = getattr(message, 'reasoning', '')

                print(f"📊 LMStudio response details:")
                print(f"   - content length: {len(content)} chars")
                print(f"   - reasoning length: {len(reasoning)} chars")
                print(f"   - content preview: {content[:100] if content else '(empty)'}...")

                # 🔧 FIX: If content is empty, try to use reasoning field
                if not content or content.strip() == "":
                    if reasoning and reasoning.strip():
                        print(f"⚠️ LMStudio returned empty content, using reasoning field ({len(reasoning)} chars)")
                        content = reasoning
                    else:
                        print(f"❌ Both content and reasoning are empty!")
                        raise Exception("LMStudio returned empty content and reasoning")

                print(f"✅ LMStudio final response: {len(content)} chars")
                return content

            except asyncio.TimeoutError:
                elapsed = time.time() - attempt_start
                print(f"⏱️ LMStudio timeout after {elapsed:.2f}s (limit: 45s)")
                print(f"💡 Hint: LMStudio should respond within 45s if model is loaded")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 2 seconds... (attempt {attempt + 2}/{max_retries})")
                    await asyncio.sleep(2)
                else:
                    print(f"❌ LMStudio failed: All {max_retries} attempt(s) timed out")
                    raise Exception(f"LMStudio timeout after {max_retries} attempt(s) (45s each - check if model is loaded)")
            except Exception as e:
                elapsed = time.time() - attempt_start
                error_msg = str(e)
                print(f"⚠️ LMStudio error after {elapsed:.2f}s: {type(e).__name__}: {error_msg}")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 2 seconds... (attempt {attempt + 2}/{max_retries})")
                    await asyncio.sleep(2)
                else:
                    print(f"❌ LMStudio failed after {max_retries} attempts")
                    import traceback
                    print(f"📋 Full error traceback:\n{traceback.format_exc()}")
                    raise Exception(f"LMStudio failed after {max_retries} attempts: {error_msg}")
    
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

    async def _query_gemini(self, system_message: str, user_prompt: str) -> str:
        """Query Gemini with timeout using new google.genai SDK"""
        gemini_config = self.clients["gemini"]  # Dict with client and model_name
        client = gemini_config["client"]
        model_name = gemini_config["model_name"]

        try:
            loop = asyncio.get_event_loop()

            # Combine system message and user prompt for Gemini
            full_prompt = f"{system_message}\n\n{user_prompt}"

            print(f"📤 Sending request to Gemini (model: {model_name})...")
            print(f"   - Prompt length: {len(full_prompt)} chars")

            # Use new SDK with timeout already configured in client
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=model_name,
                    contents=full_prompt
                )
            )

            print(f"📥 Received response from Gemini")
            return response.text

        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "deadline" in error_msg.lower():
                raise Exception("Gemini timeout after 180 seconds")
            raise Exception(f"Gemini failed: {error_msg}")

    def format_comparative_results(self, results: Dict[str, Any], feature_comparison: str = "", sensor_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Format results for frontend display with optional sensor data"""
        formatted = {
            "timestamp": datetime.now().isoformat(),
            "feature_analysis": feature_comparison,
            "llm_analyses": {},
            "performance_summary": {}
        }

        # Include sensor data if provided
        if sensor_data:
            formatted["sensor_data"] = sensor_data

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

