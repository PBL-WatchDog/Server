from flask import Blueprint

temp = Blueprint('temp', __name__)

from . import day, last, range, week