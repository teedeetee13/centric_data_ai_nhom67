"""Start the local demo from any working directory."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

def main():
    parser=argparse.ArgumentParser(description='Chạy EduSupportAI trên máy cá nhân')
    parser.add_argument('--port',type=int,default=8501)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    try:
        import streamlit
        import sklearn
    except ImportError:
        print('Chưa cài thư viện. Chạy: python -m pip install -r requirements.txt')
        return 1
    env=os.environ.copy()
    env['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
    command=[sys.executable,'-m','streamlit','run',str(root/'app'/'main.py'),
             '--server.address=127.0.0.1','--server.port='+str(args.port),
             '--browser.gatherUsageStats=false']
    return subprocess.call(command,cwd=root,env=env)

if __name__=='__main__':
    raise SystemExit(main())
