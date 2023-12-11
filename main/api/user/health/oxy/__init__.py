from flask import Blueprint

oxy = Blueprint('oxy', __name__)

from . import add, last, range, today