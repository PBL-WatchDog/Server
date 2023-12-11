from flask import Blueprint
from .door import door
from .humi import humi
from .motion import motion
from .temp import temp
from .plug import plug

activity = Blueprint('activity', __name__)
activity.register_blueprint(door, url_prefix='/door')
activity.register_blueprint(humi, url_prefix='/humi')
activity.register_blueprint(motion, url_prefix='/motion')
activity.register_blueprint(temp, url_prefix='/temp')
activity.register_blueprint(plug, url_prefix='/plug')

from . import main