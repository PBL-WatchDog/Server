from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta

from main.config import permission, mysql_connector
from main.utils import numberutil
from ..user.health._figure import figure as care_score, state as care_state
from .health._check import check as health_check
from .safety._figure import figure as safty_figure

from . import mngr

@mngr.route('/main', methods=['GET'])
@jwt_required()
def get_main_by_recent():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403
    
    offset = numberutil.to_int(request.args.get('offset', '0'))

    results = mysql_connector.sql_execute("SELECT user_id, User.name, gateway_id FROM User WHERE User.admin = %s", (user_id, ), True)

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start_date_obj = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).astimezone(timezone(timedelta(minutes=-offset)))
    end_date_obj = now + timedelta(days=1)

    response = []

    gateway_ids = [result.get("gateway_id") for result in results]
    scores = care_score(gateway_ids, datetime(1900, 1, 1, tzinfo=timezone.utc), end_date_obj)
    check = health_check(gateway_ids, start_date_obj, start_date_obj + timedelta(days=1))
    safety = safty_figure(gateway_ids)

    for result in results:
        res = {}
        res["name"] = result.get("name", '')
        res["user_id"] = result.get("user_id", '')
        score = scores.get(result.get("gateway_id"), 0)
        res["state"] = care_state[score]
        res["score"] = score
        res['check'] = check.get(result.get("gateway_id"), {})
        res['safety'] = safety.get(result.get("gateway_id"), None)
        response.append(res)

    return jsonify(response), 200