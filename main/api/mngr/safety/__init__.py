from flask import Blueprint

safety = Blueprint('safety', __name__)
GAS_DECTECTOR_CLUSTER_ON_FLAG = "210000010000"
GAS_DECTECTOR_CO_OFF_FLAG = "0"

from . import state, list