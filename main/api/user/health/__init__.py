from flask import Blueprint
from .bp import bp
from .bs import bs
from .oxy import oxy

health = Blueprint('health', __name__)
health.register_blueprint(bp, url_prefix='/bp')
health.register_blueprint(bs, url_prefix='/bs')
health.register_blueprint(oxy, url_prefix='/oxy')

from . import check, state