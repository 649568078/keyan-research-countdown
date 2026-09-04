import sys
from pathlib import Path

from flask import Flask

from .database import init_database
from .routes import bp


def default_database_path(app):
    if getattr(sys, "frozen", False):
        # PyInstaller 单文件会解压到临时目录；可写数据必须放在 EXE 外部。
        data_dir = Path(sys.executable).resolve().parent / "data"
    else:
        data_dir = Path(app.instance_path)
    return data_dir / "countdowns.sqlite3"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(default_database_path(app)),
        JSON_AS_ASCII=False,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    init_database(app)
    app.register_blueprint(bp)
    return app
