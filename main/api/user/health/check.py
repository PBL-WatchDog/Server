from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from main.config import mysql_connector, influxDB_client, permission
from main.utils import dateutil, numberutil

from . import health
from ._figure import figure as care_score, state as care_state

@health.route('/check', methods=['GET'])
@jwt_required()
def get_check_by_recent():
    user_id, auth, _ = get_jwt_identity().split(':')
    offset = numberutil.to_int(request.args.get('offset', '0'))

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    if offset is None:
        return jsonify({"msg":"invalid parameter"}), 422

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    start_date_obj = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_date_obj = dateutil.get_local_datetime(start_date_obj, offset)
    end_date_obj = start_date_obj + timedelta(days=1)

    results = mysql_connector.sql_execute("SELECT user_id, User.name, gateway_id FROM User WHERE User.admin = (SELECT admin FROM User WHERE user_id = %s)", (user_id, ), True)

    gateway_ids = [result.get("gateway_id") for result in results]
    gateway_ids_filter = ' '.join([f'r["mac_address"] == "{id}" or' for id in gateway_ids])[:-3]

    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "SensorData")
                |> filter(fn: (r) => {gateway_ids_filter})
                |> filter(fn: (r) => r["Device"] == "bp_meter" or r["Device"] == "bs_meter" or r["Device"] == "oxymeter")
                |> last()
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """
    today_states = influxDB_client.fastQuery(query)
    today_states_dict = defaultdict(dict)
    for today_state in today_states:
        gateway_id = today_state.get('mac_address')
        today_state_dict = today_states_dict[gateway_id]
        if today_state.get('diastolic') and today_state.get('systolic'):
            today_state_dict['bp'] = True
        if today_state.get('bld_sugar'):
            today_state_dict['bs'] = True
        if today_state.get('spo2') and today_state.get('bpm'):
            today_state_dict['ox'] = True

    
    scores = care_score(gateway_ids, datetime(1900, 1, 1, tzinfo=timezone.utc), end_date_obj)
    
    response = []
    for result in results:
        gateway_id = result.get('gateway_id')
        score = scores.get(gateway_id, 0)

        response.append({
            "name":result.get("name", ''),
            "user_id":result.get("user_id", ''),
            "bp":today_states_dict[gateway_id].get('bp', False),
            "bs":today_states_dict[gateway_id].get('bs', False),
            "ox":today_states_dict[gateway_id].get('ox', False),
            "state": care_state[score],
            'score':score
        })
    return jsonify(response), 200