from flask import Blueprint
from .activity import activity
from .device import device
from .health import health
from .safety import safety

mngr = Blueprint('mngr', __name__)
mngr.register_blueprint(activity, url_prefix='/activity')
mngr.register_blueprint(device, url_prefix='/device')
mngr.register_blueprint(health, url_prefix='/health')
mngr.register_blueprint(safety, url_prefix='/safety')

from . import main