from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import permission
from main.utils import mysql_query

from datetime import datetime, timezone, timedelta

from . import health
from ._figure import state, figure

state = ["good", "careful", "warning", "danger", "emergency"]

# 건강돌폼지표
@health.route('/state', methods=["GET"])
@jwt_required()
def get_indicator_by_state():
    """
    - 0 : 건강
    - 1 : 건강 조심
    - 2 : 건강 주의
    - 3 : 건강 위험
    - 4 : 응급
    """
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start_date_obj = datetime(1900, 1, 1, tzinfo=timezone.utc)
    end_date_obj = now + timedelta(days=1)

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    score = figure(gateway_id, start_date_obj, end_date_obj)
    
    return jsonify({"msg":"success", "state":state[score], 'score':score})