"""
Flask 应用入口文件
"""
import sys
import webbrowser
from backend import create_app
from backend.config import Config

app = create_app()

if __name__ == '__main__':
    if Config.DEPLOY_MODE == 'desktop':
        from backend.extensions import task_queue
        task_queue.start_worker(app)
        url = f"http://127.0.0.1:{Config.APP_PORT}"
        print(f"Desktop 模式启动 — {url}")
        if getattr(sys, 'frozen', False):
            webbrowser.open(url)
        app.run(host='127.0.0.1', port=Config.APP_PORT, threaded=True)
    else:
        app.run(host='0.0.0.0', port=Config.APP_PORT, debug=False)
