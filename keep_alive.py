"""
防冷启动脚本 - 定时访问 Streamlit 应用
用法：python keep_alive.py
或部署为 GitHub Actions（见 .github/workflows/keep-awake.yml）
"""
import requests
import time
import sys

APP_URL = "https://xxx.streamlit.app"  # 改成你的实际地址

def ping():
    try:
        r = requests.get(APP_URL, timeout=30)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ping! Status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        APP_URL = sys.argv[1]

    print(f"Keep-alive started for: {APP_URL}")
    print("Press Ctrl+C to stop")

    while True:
        ping()
        time.sleep(50 * 60)  # 每 50 分钟
