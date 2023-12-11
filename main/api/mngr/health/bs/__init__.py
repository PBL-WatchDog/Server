from flask import Blueprint

bs = Blueprint('bs', __name__)

from . import add, last, range, today