import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(ROOT_DIR)
os.environ["STREAMLIT_CONFIG_DIR"] = os.path.join(ROOT_DIR, ".streamlit")
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
os.environ["BROWSER_GATHER_USAGE_STATS"] = "false"
os.environ["STREAMLIT_GATHER_USAGE_STATS"] = "false"

subprocess.run([
    sys.executable,
    "-m",
    "streamlit",
    "run",
    "app.py",
    "--server.headless=true",
    "--client.toolbarMode=minimal",
])
