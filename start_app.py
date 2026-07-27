#!/usr/bin/env python3
"""
AIBOX启动脚本：同时启动定时任务调度器和Streamlit应用
"""

import os
import sys
import subprocess
import threading
import time

def start_scheduler():
    """启动定时任务调度器"""
    print("🚀 启动定时任务调度器...")
    scheduler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduler.py")
    subprocess.Popen([sys.executable, scheduler_path])

def start_streamlit():
    """启动Streamlit应用"""
    print("🚀 启动Streamlit应用...")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.environ["STREAMLIT_CONFIG_DIR"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit")
    
    # 启动Streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true"])

if __name__ == "__main__":
    print("=" * 60)
    print("📦 AIBOX AI日报智能体启动")
    print("=" * 60)
    
    # 启动定时任务调度器（后台线程）
    scheduler_thread = threading.Thread(target=start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # 等待调度器启动
    time.sleep(2)
    
    # 启动Streamlit应用（主线程）
    start_streamlit()
