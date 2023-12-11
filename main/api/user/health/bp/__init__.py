from flask import Blueprint

bp = Blueprint('bp', __name__)

from . import add, last, range, today