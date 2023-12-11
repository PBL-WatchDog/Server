from flask import Blueprint

safety = Blueprint('safety', __name__)

from . import state