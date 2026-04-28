import os
import sys


def is_frozen() -> bool:
    return getattr(sys, 'frozen', False)


def get_base_dir() -> str:
    """打包资源根目录（frontend/dist 等只读资源）"""
    if is_frozen():
        return sys._MEIPASS
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def get_runtime_dir() -> str:
    """运行时可写目录（data/、uploads/、outputs/、.env）"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


def get_frontend_dist() -> str:
    return os.path.join(get_base_dir(), 'frontend', 'dist')


def get_data_dir() -> str:
    d = os.path.join(get_runtime_dir(), 'data')
    os.makedirs(d, exist_ok=True)
    return d


def get_upload_dir() -> str:
    d = os.path.join(get_runtime_dir(), 'uploads')
    os.makedirs(d, exist_ok=True)
    return d


def get_output_dir() -> str:
    d = os.path.join(get_runtime_dir(), 'outputs')
    os.makedirs(d, exist_ok=True)
    return d


def get_dotenv_path() -> str:
    return os.path.join(get_runtime_dir(), '.env')
