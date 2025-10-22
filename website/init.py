from flask import Flask
from .auth import auth
from .views import views
from .enrollment import enrollment
from .timetable import timetable
from .admin_views import admin_views
from .admin_proposal import admin_proposal
from .lecturer_views import lecturer_views  
def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = 'asgdfbsv'
    app.register_blueprint(auth)
    app.register_blueprint(views)
    app.register_blueprint(enrollment, url_prefix='/')
    app.register_blueprint(timetable)
    app.register_blueprint(admin_views)
    app.register_blueprint(admin_proposal)
    app.register_blueprint(lecturer_views, url_prefix='/')
    return app
