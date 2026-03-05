import os
from flask import send_from_directory
from backend import create_app

# 调用工厂函数创建应用实例
app = create_app()

@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/admin.html')
def serve_admin():
    return send_from_directory(app.static_folder, 'admin.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    # 从 Flask 配置中读取我们写入的 IP 和 Port
    host = app.config.get('APP_HOST', '0.0.0.0')
    port = app.config.get('APP_PORT', 8000)
    
    print(f"\n🚀 AI 学术写作助手 - 启动中...")
    print(f"📍 用户入口: http://{host}:{port}")
    print(f"📍 管理后台: http://{host}:{port}/admin.html\n")
    
    app.run(host=host, port=port, debug=True)