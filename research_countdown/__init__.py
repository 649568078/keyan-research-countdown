from pathlib import Path

from flask import Flask

from .database import init_database
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "countdowns.sqlite3"),
        JSON_AS_ASCII=False,
    )
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_database(app)
    app.register_blueprint(bp)
    return app

