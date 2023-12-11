from flask import Blueprint

motion = Blueprint('motion', __name__)

ON_FLAG = ["010000FF0000", "010000010000"]
DEVICE_TYPE = 'motion'

from . import day, last, range, week