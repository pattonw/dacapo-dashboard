import os

from flask import Flask, render_template
from flask_login.utils import login_required
from flask_socketio import SocketIO

socketio = SocketIO()


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=os.path.join(app.instance_path, "flaskr.sqlite"),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile("config.py", silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from .authservice import create_login_manager

    create_login_manager(app)

    # a simple page that says hello
    @app.route("/hello")
    @login_required
    def hello():
        return "Hello, World!"

    @app.route("/")
    def main():
        return render_template("base.html")

    from . import stores

    app.config["stores"] = stores.get_or_create_stores_as_named_tuple()

    from . import auth

    app.register_blueprint(auth.bp)

    from . import dacapo

    app.register_blueprint(dacapo.bp)

    socketio.init_app(app)
    return app
