from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import permission, mysql_connector
from main.utils import dateutil
from datetime import datetime, timezone, timedelta

from . import activity
from ._graph import graph, DAY_OPTION

@activity.route('/overall', methods=['GET'])
@jwt_required()
def get_overall_by_activity():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403

    results = mysql_connector.sql_execute("SELECT user_id, gateway_id FROM User WHERE User.admin = %s", (user_id, ), True)

    gateway_ids = [result.get("gateway_id") for result in results]

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    graph_data = graph(gateway_ids, now)

    data = {result.get('user_id') : graph_data.get(result.get('gateway_id')) for result in results}

    start = now - timedelta(days=DAY_OPTION)
    response = {"range" : { "start" : dateutil.get_utc_isoformat(start), "end" : dateutil.get_utc_isoformat(now) }, "data" : data}

    return jsonify(response)