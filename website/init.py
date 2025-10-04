from flask import Flask
from .auth import auth
from .views import views
from .enrollment import enrollment
def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = 'quang anh dep trai vocolo'
    app.register_blueprint(auth)
    app.register_blueprint(views)
    app.register_blueprint(enrollment, url_prefix='/')
    return app
