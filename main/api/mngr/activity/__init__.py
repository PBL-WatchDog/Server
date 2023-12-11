from flask import Blueprint
from .door import door
from .humi import humi
from .temp import temp
from .motion import motion
from .tv import tv

activity = Blueprint('activity', __name__)
activity.register_blueprint(door, url_prefix='/door')
activity.register_blueprint(humi, url_prefix='/humi')
activity.register_blueprint(motion, url_prefix='/motion')
activity.register_blueprint(temp, url_prefix='/temp')
activity.register_blueprint(tv, url_prefix='/tv')

from . import main, overall