"""Start the local demo from any working directory."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

def ensure_ollama():
    """Bật Ollama nếu đã cài mà chưa chạy; không có Ollama thì app dùng bản nháp theo mẫu."""
    import shutil
    import time
    import urllib.request
    host=os.environ.get('OLLAMA_HOST','http://127.0.0.1:11434').rstrip('/')
    def running():
        try:
            urllib.request.urlopen(host+'/api/version',timeout=2)
            return True
        except OSError:
            return False
    if os.environ.get('EDUSUPPORT_LLM','auto').lower()=='off' or running():
        return
    exe=shutil.which('ollama') or str(Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'Ollama'/'ollama.exe')
    if not Path(exe).exists():
        print('Chưa cài Ollama: bản nháp sẽ dùng mẫu câu. Xem readme mục 8.3 để bật mô hình ngôn ngữ cục bộ.')
        return
    flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
    subprocess.Popen([exe,'serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=flags)
    for _ in range(15):
        if running():
            print('Đã bật Ollama cho mô hình ngôn ngữ cục bộ.')
            return
        time.sleep(1)
    print('Không bật được Ollama; app vẫn chạy với bản nháp theo mẫu.')

def main():
    parser=argparse.ArgumentParser(description='Chạy EduSupportAI trên máy cá nhân')
    parser.add_argument('--port',type=int,default=8501)
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    import importlib.util
    if not all(importlib.util.find_spec(m) for m in ('streamlit','sklearn')):
        print('Chưa cài thư viện. Chạy: python -m pip install -r requirements.txt')
        return 1
    ensure_ollama()
    env=os.environ.copy()
    env['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
    command=[sys.executable,'-m','streamlit','run',str(root/'app'/'main.py'),
             '--server.address=127.0.0.1','--server.port='+str(args.port),
             '--browser.gatherUsageStats=false']
    return subprocess.call(command,cwd=root,env=env)

if __name__=='__main__':
    raise SystemExit(main())
