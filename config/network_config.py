#!/usr/bin/env python3
"""
网络配置工具 - 获取本机IP地址并更新配置文件
解决Mac Safari访问localhost的问题
"""

import socket
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any

class NetworkConfigManager:
    """网络配置管理器"""
    
    def __init__(self):
        self.local_ip = self.get_local_ip()
        self.config_files = [
            "backend/config.json",
            "frontend/config.json",
            "config.json"
        ]
    
    def get_local_ip(self) -> str:
        """获取本机IP地址"""
        try:
            # 方法1: 连接外部地址获取本机IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            try:
                # 方法2: 使用ifconfig命令 (Mac/Linux)
                result = subprocess.run(['ifconfig'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'inet ' in line and '127.0.0.1' not in line and 'inet 169.254' not in line:
                        ip = line.split('inet ')[1].split(' ')[0]
                        if self.is_valid_ip(ip):
                            return ip
            except Exception:
                pass
            
            try:
                # 方法3: 使用hostname命令
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                if ip != '127.0.0.1':
                    return ip
            except Exception:
                pass
        
        # 默认返回localhost
        return '127.0.0.1'
    
    def is_valid_ip(self, ip: str) -> bool:
        """验证IP地址格式"""
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False
    
    def get_network_info(self) -> Dict[str, str]:
        """获取网络信息"""
        return {
            "local_ip": self.local_ip,
            "faultexplainer_backend": f"http://{self.local_ip}:8000",
            "faultexplainer_frontend": f"http://{self.local_ip}:3000", 
            "streamlit_app": f"http://{self.local_ip}:8501",
            "safari_compatible": True if self.local_ip != '127.0.0.1' else False
        }
    
    def update_config_file(self, config_path: str) -> bool:
        """更新配置文件中的IP地址"""
        try:
            config_path = Path(config_path)
            if not config_path.exists():
                print(f"⚠️ Config file not found: {config_path}")
                return False
            
            # 读取现有配置
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新IP相关配置
            updated = False
            
            # 更新LMStudio URL
            if 'lmstudio' in config:
                old_url = config['lmstudio'].get('base_url', '')
                new_url = f"http://{self.local_ip}:1234/v1"
                if old_url != new_url:
                    config['lmstudio']['base_url'] = new_url
                    updated = True
            
            # 更新其他可能的localhost引用
            config_str = json.dumps(config)
            if 'localhost' in config_str or '127.0.0.1' in config_str:
                config_str = config_str.replace('localhost', self.local_ip)
                config_str = config_str.replace('127.0.0.1', self.local_ip)
                config = json.loads(config_str)
                updated = True
            
            # 保存更新后的配置
            if updated:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print(f"✅ Updated config: {config_path}")
                return True
            else:
                print(f"ℹ️ No updates needed: {config_path}")
                return True
                
        except Exception as e:
            print(f"❌ Error updating {config_path}: {e}")
            return False
    
    def update_python_files(self) -> bool:
        """更新Python文件中的localhost引用"""
        python_files = [
            "backend/tep_faultexplainer_bridge.py",
            "backend/app.py",
            "unified_console.py"
        ]
        
        updated_files = []
        
        for file_path in python_files:
            try:
                file_path = Path(file_path)
                if not file_path.exists():
                    continue
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否需要更新
                if 'localhost:8000' in content or '127.0.0.1:8000' in content:
                    # 替换localhost引用
                    new_content = content.replace('localhost:8000', f'{self.local_ip}:8000')
                    new_content = new_content.replace('127.0.0.1:8000', f'{self.local_ip}:8000')
                    new_content = new_content.replace('localhost:3000', f'{self.local_ip}:3000')
                    new_content = new_content.replace('127.0.0.1:3000', f'{self.local_ip}:3000')
                    new_content = new_content.replace('localhost:8501', f'{self.local_ip}:8501')
                    new_content = new_content.replace('127.0.0.1:8501', f'{self.local_ip}:8501')
                    
                    # 保存更新后的文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    updated_files.append(str(file_path))
                    print(f"✅ Updated Python file: {file_path}")
                
            except Exception as e:
                print(f"❌ Error updating {file_path}: {e}")
        
        return len(updated_files) > 0
    
    def create_network_settings_file(self):
        """创建网络设置文件"""
        settings = {
            "network_info": self.get_network_info(),
            "last_updated": "2024-01-15T10:00:00Z",
            "safari_instructions": {
                "step1": f"Open Safari and navigate to {self.local_ip}:3000",
                "step2": "If prompted about security, click 'Advanced' then 'Proceed'",
                "step3": "Bookmark the IP address for future use"
            },
            "troubleshooting": {
                "firewall": "Check macOS firewall settings if connection fails",
                "network": "Ensure you're on the same network as the server",
                "ports": "Verify ports 3000, 8000, 8501 are not blocked"
            }
        }
        
        with open('network_settings.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Created network settings file: network_settings.json")
    
    def test_network_connectivity(self) -> Dict[str, bool]:
        """测试网络连接"""
        results = {}
        
        # 测试端口是否可用
        ports_to_test = [3000, 8000, 8501]
        
        for port in ports_to_test:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.local_ip, port))
                sock.close()
                
                if result == 0:
                    results[f"port_{port}"] = True
                    print(f"✅ Port {port} is available")
                else:
                    results[f"port_{port}"] = False
                    print(f"❌ Port {port} is not available")
                    
            except Exception as e:
                results[f"port_{port}"] = False
                print(f"❌ Error testing port {port}: {e}")
        
        return results
    
    def generate_startup_urls(self) -> Dict[str, str]:
        """生成启动URL"""
        return {
            "FaultExplainer Frontend": f"http://{self.local_ip}:3000",
            "FaultExplainer Backend API": f"http://{self.local_ip}:8000",
            "FaultExplainer Status": f"http://{self.local_ip}:8000/status",
            "AI Agent Status": f"http://{self.local_ip}:8000/ai_agent/status",
            "Streamlit RAG Chat": f"http://{self.local_ip}:8501"
        }

def main():
    """主函数"""
    print("🌐 TEP Network Configuration Tool")
    print("=" * 50)
    
    # 初始化网络配置管理器
    config_manager = NetworkConfigManager()
    
    # 显示网络信息
    network_info = config_manager.get_network_info()
    print(f"\n📡 Network Information:")
    print(f"Local IP: {network_info['local_ip']}")
    print(f"Safari Compatible: {'✅ Yes' if network_info['safari_compatible'] else '❌ No'}")
    
    # 显示访问URL
    print(f"\n🔗 Access URLs:")
    urls = config_manager.generate_startup_urls()
    for name, url in urls.items():
        print(f"  {name}: {url}")
    
    # 更新配置文件
    print(f"\n🔧 Updating Configuration Files:")
    for config_file in config_manager.config_files:
        if Path(config_file).exists():
            config_manager.update_config_file(config_file)
    
    # 更新Python文件
    print(f"\n🐍 Updating Python Files:")
    config_manager.update_python_files()
    
    # 创建网络设置文件
    print(f"\n📄 Creating Network Settings:")
    config_manager.create_network_settings_file()
    
    # 测试网络连接
    print(f"\n🧪 Testing Network Connectivity:")
    connectivity_results = config_manager.test_network_connectivity()
    
    # 显示Safari使用说明
    print(f"\n🧭 Safari Usage Instructions:")
    print(f"1. Open Safari")
    print(f"2. Navigate to: {network_info['faultexplainer_frontend']}")
    print(f"3. If security warning appears, click 'Advanced' → 'Proceed'")
    print(f"4. Bookmark the IP address for future use")
    
    print(f"\n✅ Network configuration completed!")
    print(f"📋 Next steps:")
    print(f"   1. Start the TEP services using the updated IP addresses")
    print(f"   2. Test access from Safari using the provided URLs")
    print(f"   3. Check network_settings.json for troubleshooting info")

if __name__ == "__main__":
    main()
