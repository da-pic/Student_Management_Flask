from flask import Flask
from .auth import auth
from .views import views
from .enrollment import enrollment
from .timetable import timetable
def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = 'quang anh dep trai vocolo'
    app.register_blueprint(auth)
    app.register_blueprint(views)
    app.register_blueprint(enrollment, url_prefix='/')
    app.register_blueprint(timetable)
    return app
