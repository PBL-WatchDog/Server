from flask import Blueprint

humi = Blueprint('humi', __name__)

from . import day, last, range, week