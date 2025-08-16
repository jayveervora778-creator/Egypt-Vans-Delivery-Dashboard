#!/usr/bin/env python3
import subprocess
import sys
import os

def start_streamlit():
    os.chdir('/home/user/webapp_fresh')
    
    # Start streamlit with specific settings
    cmd = [
        sys.executable, '-m', 'streamlit', 'run', 'app.py',
        '--server.port', '3000',
        '--server.address', '0.0.0.0',
        '--server.headless', 'true',
        '--server.runOnSave', 'false',
        '--server.fileWatcherType', 'none'
    ]
    
    print("Starting Vans Dashboard on port 3000...")
    subprocess.run(cmd)

if __name__ == "__main__":
    start_streamlit()