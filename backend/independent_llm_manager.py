#!/usr/bin/env python3
"""
Independent LLM Manager - Each model manages itself independently
每个模型独立管理，互不干扰
"""

import asyncio
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class IndependentModelManager:
    """独立模型管理器 - 每个模型有自己的状态和时间周期"""
    
    def __init__(self, model_name: str, multi_llm_client, display_duration: int = 7):
        self.model_name = model_name
        self.client = multi_llm_client
        self.display_duration = display_duration  # 结果显示时间（秒）
        
        # 独立状态管理
        self.is_analyzing = False
        self.is_displaying = False
        self.last_analysis_time = 0
        self.current_result = None
        self.result_timestamp = None

        # 创建结果存储目录 - 保存到TEP_control/RCA_Results
        backend_dir = Path(__file__).parent
        tep_control_dir = backend_dir.parent
        self.results_dir = tep_control_dir / "RCA_Results"
        self.results_dir.mkdir(exist_ok=True)
        
        # 创建今日的MD文件
        today = datetime.now().strftime("%m%d")
        if model_name == "mistral":
            self.log_file = self.results_dir / f"LocalLLM_{today}.md"
        elif model_name == "lmstudio":
            self.log_file = self.results_dir / f"LMStudio_{today}.md"
        elif model_name == "gemini":
            self.log_file = self.results_dir / f"Gemini_{today}.md"
        else:
            self.log_file = self.results_dir / f"{model_name}_{today}.md"
            
        # 初始化日志文件
        self._init_log_file()
    
    def _init_log_file(self):
        """初始化MD日志文件"""
        if not self.log_file.exists():
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(f"# {self.model_name.upper()} Root Cause Analysis Log\n\n")
                f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n")
                f.write(f"**Model**: {self.model_name}\n\n")
                f.write("---\n\n")
    
    def can_accept_request(self) -> bool:
        """检查是否可以接受新的分析请求"""
        return not (self.is_analyzing or self.is_displaying)
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "model_name": self.model_name,
            "is_analyzing": self.is_analyzing,
            "is_displaying": self.is_displaying,
            "can_accept": self.can_accept_request(),
            "current_result": self.current_result,
            "result_timestamp": self.result_timestamp,
            "last_analysis_time": self.last_analysis_time
        }
    
    async def analyze_fault(self, system_message: str, user_prompt: str, fault_features: list = None) -> Dict[str, Any]:
        """独立分析故障 - 不受其他模型影响"""
        
        if not self.can_accept_request():
            return {
                "status": "busy",
                "message": f"{self.model_name} is currently busy (analyzing or displaying results)",
                "can_retry_after": self._get_retry_time()
            }
        
        # 开始分析
        self.is_analyzing = True
        analysis_start_time = time.time()
        
        try:
            logger.info(f"🤖 {self.model_name} starting independent analysis...")
            
            # 调用对应的模型
            if self.model_name == "mistral":
                response = await self.client._query_mistral(system_message, user_prompt)
            elif self.model_name == "gemini":
                response = await self.client._query_gemini(system_message, user_prompt)
            elif self.model_name == "lmstudio":
                response = await self.client._query_lmstudio(system_message, user_prompt)
            elif self.model_name == "anthropic":
                response = await self.client._query_claude(system_message, user_prompt)
            else:
                raise ValueError(f"Unknown model: {self.model_name}")
            
            analysis_end_time = time.time()
            analysis_duration = round(analysis_end_time - analysis_start_time, 2)
            
            # 准备结果
            result = {
                "model_name": self.model_name,
                "response": response,
                "analysis_duration": analysis_duration,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
            # 保存到MD文件
            self._save_to_md(result, fault_features)
            
            # 设置显示状态
            self.current_result = result
            self.result_timestamp = time.time()
            self.is_analyzing = False
            self.is_displaying = True
            
            # 启动显示计时器
            asyncio.create_task(self._display_timer())
            
            logger.info(f"✅ {self.model_name} analysis completed in {analysis_duration}s")
            return result
            
        except Exception as e:
            self.is_analyzing = False
            error_result = {
                "model_name": self.model_name,
                "response": f"Error: {str(e)}",
                "analysis_duration": 0,
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
            
            # 也保存错误到MD文件
            self._save_to_md(error_result, fault_features)
            
            logger.error(f"❌ {self.model_name} analysis failed: {str(e)}")
            return error_result
    
    def _save_to_md(self, result: Dict[str, Any], fault_features: list = None):
        """保存结果到MD文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"## Analysis at {result['timestamp']}\n\n")
                f.write(f"**Duration**: {result['analysis_duration']}s\n")
                f.write(f"**Status**: {result['status']}\n")
                
                if fault_features:
                    f.write(f"**Top Features**: {', '.join(fault_features[:6])}\n")
                
                f.write(f"\n### Root Cause Analysis:\n\n")
                f.write(f"{result['response']}\n\n")
                f.write("---\n\n")
                
        except Exception as e:
            logger.error(f"Failed to save {self.model_name} result to MD: {str(e)}")
    
    async def _display_timer(self):
        """显示计时器 - 控制结果显示时间"""
        await asyncio.sleep(self.display_duration)
        self.is_displaying = False
        self.last_analysis_time = time.time()
        logger.info(f"📱 {self.model_name} display period ended, ready for next analysis")
    
    def _get_retry_time(self) -> float:
        """获取可以重试的时间"""
        if self.is_analyzing:
            return 0  # 分析中，无法预测完成时间
        elif self.is_displaying and self.result_timestamp:
            remaining = self.display_duration - (time.time() - self.result_timestamp)
            return max(0, remaining)
        return 0
    
    def freeze_display(self):
        """冻结显示 - 用户可以仔细查看结果"""
        if self.is_displaying:
            self.is_displaying = "frozen"  # 特殊状态
            logger.info(f"🧊 {self.model_name} display frozen by user")
    
    def unfreeze_display(self):
        """解冻显示"""
        if self.is_displaying == "frozen":
            self.is_displaying = False
            self.last_analysis_time = time.time()
            logger.info(f"🔥 {self.model_name} display unfrozen, ready for next analysis")


class IndependentLLMSystem:
    """独立LLM系统管理器"""
    
    def __init__(self, multi_llm_client):
        self.client = multi_llm_client
        self.managers: Dict[str, IndependentModelManager] = {}
        
        # 为每个启用的模型创建独立管理器
        # LM Studio: ~30s分析 + 10s显示 = 40s周期
        # Gemini: ~20s分析 + 7s显示 = 27s周期
        display_durations = {
            "mistral": 7,      # Local LLM显示7秒 (已禁用)
            "lmstudio": 10,    # LM Studio显示10秒
            "gemini": 7,       # Gemini显示7秒
            "anthropic": 7
        }
        
        for model_name in self.client.enabled_models:
            duration = display_durations.get(model_name, 7)
            self.managers[model_name] = IndependentModelManager(
                model_name, self.client, duration
            )
            logger.info(f"🔧 Created independent manager for {model_name} (display: {duration}s)")
    
    async def analyze_with_model(self, model_name: str, system_message: str, user_prompt: str, fault_features: list = None) -> Dict[str, Any]:
        """使用指定模型进行独立分析"""
        if model_name not in self.managers:
            return {
                "status": "error",
                "message": f"Model {model_name} not available"
            }
        
        return await self.managers[model_name].analyze_fault(system_message, user_prompt, fault_features)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型的状态"""
        return {name: manager.get_status() for name, manager in self.managers.items()}
    
    def freeze_model_display(self, model_name: str):
        """冻结指定模型的显示"""
        if model_name in self.managers:
            self.managers[model_name].freeze_display()
    
    def unfreeze_model_display(self, model_name: str):
        """解冻指定模型的显示"""
        if model_name in self.managers:
            self.managers[model_name].unfreeze_display()
