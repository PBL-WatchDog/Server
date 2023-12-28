from flask import Blueprint
from .ml import ml
from .statistics import statistics

report = Blueprint('report', __name__)

report.register_blueprint(ml, url_prefix='/ml')
report.register_blueprint(statistics, url_prefix='/statistics')