# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
app_dir = os.path.join(os.getcwd(), 'app')

a = Analysis(
    [os.path.join(app_dir, 'main.py')],
    pathex=[app_dir],
    datas=[
        (os.path.join(app_dir, 'frontend', 'dist'), os.path.join('frontend', 'dist')),
    ],
    hiddenimports=[
        # --- app modules ---
        'backend',
        'backend.paths',
        'backend.config',
        'backend.extensions',
        'backend.memory_backend',
        'backend.memory_queue',
        'backend.routes.auth',
        'backend.routes.task',
        'backend.routes.admin',
        'backend.model.models',
        'backend.services.task_service',
        'backend.services.ai_service',
        'backend.services.ai_service_refactored',
        'backend.services.api_config_service',
        'backend.services.progress_publisher',
        'backend.services.cancellation_checker',
        'backend.processors.base_processor',
        'backend.processors.text_processor',
        'backend.processors.docx_processor',
        'backend.processors.pdf_processor',
        'backend.worker_engine',
        'backend.utils.helpers',
        'backend.utils.text_hash',
        'backend.utils.logging_config',
        # --- Flask ecosystem ---
        'flask',
        'flask.json',
        'flask_sqlalchemy',
        'flask_cors',
        'sqlalchemy',
        'sqlalchemy.sql.default_comparator',
        'sqlalchemy.dialects.sqlite',
        # --- core deps ---
        'dotenv',
        'waitress',
        'fitz',
        'lxml',
        'lxml.etree',
        'docx',
        'pydantic',
        'pydantic.deprecated.decorator',
        'httpx',
        'httpcore',
        'openai',
        'sqlite3',
        'jinja2',
        'markupsafe',
        'werkzeug',
        'click',
        'itsdangerous',
        'blinker',
        'certifi',
        'charset_normalizer',
        'idna',
        'sniffio',
        'anyio',
        'h11',
    ],
    excludes=[
        'mysql',
        'mysql.connector',
        'mysqlx',
        'redis',
        'rq',
        'gevent',
        'greenlet',
        'gunicorn',
        'tkinter',
        'unittest',
        'test',
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AIpolish',
    console=True,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='AIpolish',
)
