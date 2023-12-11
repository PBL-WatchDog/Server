from flask import Blueprint

device = Blueprint('device', __name__)

from . import delete, list, new, update, waiting