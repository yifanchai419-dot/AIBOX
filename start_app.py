#!/usr/bin/env python3
"""
AIBOX启动脚本：启动Streamlit应用
（调度器已集成到 app.py 内部，无需单独启动）
"""

import os
import sys
import subprocess


def start_streamlit():
    """启动Streamlit应用"""
    print("🚀 启动AIBOX AI日报智能体...")
    print("📅 调度器已集成至应用内，首次访问时自动启动")
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.environ["STREAMLIT_CONFIG_DIR"] = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit")

    # 启动Streamlit
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true"])


if __name__ == "__main__":
    print("=" * 60)
    print("📦 AIBOX AI日报智能体启动")
    print("=" * 60)

    # 启动 Streamlit 应用
    start_streamlit()
