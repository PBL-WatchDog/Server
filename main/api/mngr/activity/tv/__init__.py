from flask import Blueprint

tv = Blueprint('tv', __name__)
ON_FLAG = 20
DEVICE_TYPE = 'plug'

from . import day, last, range, week