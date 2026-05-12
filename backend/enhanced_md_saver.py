#!/usr/bin/env python3
"""
增强的MD文件保存器
解决现有系统MD文件保存问题，支持AI Agent增强分析的保存
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedMDSaver:
    """增强的MD文件保存器"""
    
    def __init__(self, base_path: str = "LLM_RCA_Results"):
        """
        初始化MD保存器
        
        Args:
            base_path: MD文件保存的基础路径
        """
        # 确保路径是绝对路径
        if not os.path.isabs(base_path):
            current_dir = Path(__file__).parent
            self.base_path = current_dir / base_path
        else:
            self.base_path = Path(base_path)
        
        # 创建目录
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 确保目录权限正确
        try:
            os.chmod(self.base_path, 0o755)
        except Exception as e:
            logger.warning(f"Could not set directory permissions: {e}")
        
        logger.info(f"✅ Enhanced MD Saver initialized at: {self.base_path}")
    
    def get_daily_filename(self, model_name: str, enhanced: bool = False) -> str:
        """
        获取每日MD文件名
        
        Args:
            model_name: 模型名称 (gemini, claude, lmstudio等)
            enhanced: 是否为AI Agent增强版本
        """
        today = datetime.now().strftime("%m%d")
        
        # 标准化模型名称
        model_mapping = {
            "gemini": "Gemini",
            "claude": "Claude", 
            "anthropic": "Claude",
            "lmstudio": "LMStudio",
            "mistral": "LocalLLM",
            "ai_agent": "AI_Agent"
        }
        
        clean_model_name = model_mapping.get(model_name.lower(), model_name.title())
        
        if enhanced:
            return f"{clean_model_name}_Enhanced_{today}.md"
        else:
            return f"{clean_model_name}_{today}.md"
    
    def init_daily_file(self, model_name: str, enhanced: bool = False) -> Path:
        """
        初始化每日MD文件
        
        Args:
            model_name: 模型名称
            enhanced: 是否为增强版本
            
        Returns:
            MD文件路径
        """
        filename = self.get_daily_filename(model_name, enhanced)
        file_path = self.base_path / filename
        
        # 如果文件不存在，创建并写入头部
        if not file_path.exists():
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    title = f"{model_name.upper()} Root Cause Analysis Log"
                    if enhanced:
                        title += " (AI Agent Enhanced)"
                    
                    f.write(f"# {title}\n\n")
                    f.write(f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n")
                    f.write(f"**Model**: {model_name}\n")
                    if enhanced:
                        f.write(f"**Enhancement**: AI Agent Knowledge System\n")
                    f.write(f"**Auto-generated**: True\n\n")
                    f.write("---\n\n")
                
                # 设置文件权限
                os.chmod(file_path, 0o644)
                logger.info(f"✅ Initialized MD file: {file_path}")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize MD file {file_path}: {e}")
                raise
        
        return file_path
    
    def save_standard_analysis(self, 
                             model_name: str,
                             analysis_result: Dict[str, Any],
                             fault_features: Optional[List[str]] = None) -> bool:
        """
        保存标准的LLM分析结果
        
        Args:
            model_name: 模型名称
            analysis_result: 分析结果字典
            fault_features: 故障特征列表
            
        Returns:
            保存是否成功
        """
        try:
            file_path = self.init_daily_file(model_name, enhanced=False)
            
            with open(file_path, 'a', encoding='utf-8') as f:
                timestamp = analysis_result.get('timestamp', datetime.now().isoformat())
                duration = analysis_result.get('analysis_duration', 'N/A')
                status = analysis_result.get('status', 'unknown')
                response = analysis_result.get('response', 'No response available')
                
                f.write(f"## Analysis at {timestamp}\n\n")
                f.write(f"**Duration**: {duration}s\n")
                f.write(f"**Status**: {status}\n")
                
                if fault_features:
                    f.write(f"**Top Features**: {', '.join(fault_features[:6])}\n")
                
                f.write(f"\n### Root Cause Analysis:\n\n")
                f.write(f"{response}\n\n")
                f.write("---\n\n")
            
            logger.info(f"✅ Saved standard analysis for {model_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save standard analysis for {model_name}: {e}")
            return False
    
    def save_enhanced_analysis(self,
                             original_analysis: Dict[str, Any],
                             ai_enhancement: str,
                             anomaly_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        保存AI Agent增强的分析结果
        
        Args:
            original_analysis: 原始Multi-LLM分析结果
            ai_enhancement: AI Agent增强分析
            anomaly_data: 异常数据
            
        Returns:
            保存是否成功
        """
        try:
            file_path = self.init_daily_file("ai_agent", enhanced=True)
            
            with open(file_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().isoformat()
                
                f.write(f"## Enhanced Analysis at {timestamp}\n\n")
                
                # 异常数据信息
                if anomaly_data:
                    f.write(f"### Anomaly Context\n\n")
                    f.write(f"- **T² Statistic**: {anomaly_data.get('t2_stat', 'N/A')}\n")
                    f.write(f"- **Threshold**: {anomaly_data.get('threshold', 'N/A')}\n")
                    f.write(f"- **Anomaly Status**: {anomaly_data.get('anomaly', 'N/A')}\n")
                    f.write(f"- **Contributing Factors**: {anomaly_data.get('contributing_factors', 'N/A')}\n\n")
                
                # 原始分析
                f.write(f"### Original Multi-LLM Analysis\n\n")
                if isinstance(original_analysis, dict):
                    # 如果是字典，格式化显示
                    for key, value in original_analysis.items():
                        if key not in ['timestamp', 'status']:
                            f.write(f"**{key.title()}**: {value}\n\n")
                else:
                    f.write(f"{original_analysis}\n\n")
                
                # AI Agent增强分析
                f.write(f"### AI Agent Enhancement\n\n")
                f.write(f"{ai_enhancement}\n\n")
                
                f.write("---\n\n")
            
            logger.info(f"✅ Saved enhanced analysis")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save enhanced analysis: {e}")
            return False
    
    def save_comparative_analysis(self,
                                multi_llm_results: Dict[str, Any],
                                ai_enhancement: Optional[str] = None) -> bool:
        """
        保存对比分析结果 (多个LLM + AI Agent增强)
        
        Args:
            multi_llm_results: 多LLM对比结果
            ai_enhancement: AI Agent增强分析
            
        Returns:
            保存是否成功
        """
        try:
            file_path = self.init_daily_file("comparative", enhanced=bool(ai_enhancement))
            
            with open(file_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().isoformat()
                
                f.write(f"## Comparative Analysis at {timestamp}\n\n")
                
                # Multi-LLM结果
                f.write(f"### Multi-LLM Results\n\n")
                
                if isinstance(multi_llm_results, dict):
                    for model, result in multi_llm_results.items():
                        if isinstance(result, dict) and 'response' in result:
                            f.write(f"#### {model.title()}\n\n")
                            f.write(f"**Status**: {result.get('status', 'unknown')}\n")
                            f.write(f"**Duration**: {result.get('response_time', 'N/A')}s\n")
                            f.write(f"**Response**: {result.get('response', 'No response')}\n\n")
                
                # AI Agent增强
                if ai_enhancement:
                    f.write(f"### AI Agent Enhancement\n\n")
                    f.write(f"{ai_enhancement}\n\n")
                
                f.write("---\n\n")
            
            logger.info(f"✅ Saved comparative analysis")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save comparative analysis: {e}")
            return False
    
    def get_recent_analyses(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取最近几天的分析记录
        
        Args:
            days: 查询天数
            
        Returns:
            分析记录列表
        """
        analyses = []
        
        try:
            # 获取所有MD文件
            md_files = list(self.base_path.glob("*.md"))
            
            for md_file in md_files:
                # 检查文件修改时间
                mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
                if (datetime.now() - mtime).days <= days:
                    analyses.append({
                        "file": md_file.name,
                        "path": str(md_file),
                        "modified": mtime.isoformat(),
                        "size": md_file.stat().st_size
                    })
            
            # 按修改时间排序
            analyses.sort(key=lambda x: x['modified'], reverse=True)
            
        except Exception as e:
            logger.error(f"❌ Failed to get recent analyses: {e}")
        
        return analyses
    
    def cleanup_old_files(self, keep_days: int = 30) -> int:
        """
        清理旧的MD文件
        
        Args:
            keep_days: 保留天数
            
        Returns:
            删除的文件数量
        """
        deleted_count = 0
        
        try:
            md_files = list(self.base_path.glob("*.md"))
            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 3600)
            
            for md_file in md_files:
                if md_file.stat().st_mtime < cutoff_time:
                    md_file.unlink()
                    deleted_count += 1
                    logger.info(f"🗑️ Deleted old file: {md_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old files: {e}")
        
        return deleted_count
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取MD保存器状态
        
        Returns:
            状态信息字典
        """
        try:
            md_files = list(self.base_path.glob("*.md"))
            total_size = sum(f.stat().st_size for f in md_files)
            
            return {
                "base_path": str(self.base_path),
                "total_files": len(md_files),
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "writable": os.access(self.base_path, os.W_OK),
                "recent_files": [f.name for f in md_files[-5:]]  # 最近5个文件
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get status: {e}")
            return {"error": str(e)}

# 全局实例
enhanced_md_saver = EnhancedMDSaver()

def save_analysis_to_md(model_name: str, 
                       analysis_result: Dict[str, Any],
                       fault_features: Optional[List[str]] = None,
                       ai_enhancement: Optional[str] = None) -> bool:
    """
    便捷函数：保存分析结果到MD文件
    
    Args:
        model_name: 模型名称
        analysis_result: 分析结果
        fault_features: 故障特征
        ai_enhancement: AI增强分析
        
    Returns:
        保存是否成功
    """
    success = enhanced_md_saver.save_standard_analysis(model_name, analysis_result, fault_features)
    
    if ai_enhancement and success:
        success = enhanced_md_saver.save_enhanced_analysis(analysis_result, ai_enhancement)
    
    return success
