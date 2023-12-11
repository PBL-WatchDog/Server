from flask import Blueprint
from .activity import activity
from .device import device
from .health import health
from .safety import safety

user = Blueprint('user', __name__)

user.register_blueprint(activity, url_prefix='/activity')
user.register_blueprint(device, url_prefix='/device')
user.register_blueprint(health, url_prefix='/health')
user.register_blueprint(safety, url_prefix='/safety')
