from flask import Blueprint

ON_FLAG = "1"
DEVICE_TYPE = "door"

door = Blueprint('door', __name__)

from . import day, last, range, week