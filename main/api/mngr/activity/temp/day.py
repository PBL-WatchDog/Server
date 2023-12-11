from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query, dateutil

import json
from datetime import timedelta

from . import temp

@temp.route('/day', methods=['GET'])
@jwt_required()
def get_temperature_by_day():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403
    
    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"invalid parameter"}), 422

    gateway_id = mysql_query.get_gateway_id_by_user_id(target_user_id, user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    target_date = request.args.get('date')
    start_date_obj = dateutil.get_datetime_by_utc_isoformat(target_date)
    if not start_date_obj:
        return jsonify({"msg":"invalid parameter"}), 422
    end_date_obj = start_date_obj + timedelta(days=1)
    
    query_api = influxDB_client.client.query_api()
    query = f"""
            import "json"

            from(bucket: "smarthome")
                |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                |> filter(fn: (r) => r._measurement == "GatewayData" and r._field == "temperature" and r.mac_address == "{gateway_id}")
                |> window(every: 1h)
                |> mean()
                |> map(fn: (r) => ({"{"}r with jsonStr: string(v: json.encode(v: {"{"}"date": r._start, "value": r._value{"}"})){"}"}))
            """
    
    tables = query_api.query(query, org="Brighten")
    result = []

    for table in tables:
        for record in table.records:
            result.append(json.loads(record.__getitem__('jsonStr')))
    
    formatted_results = []
    for item in result:
        formatted_results.append({'date': item['date'], 'value': item['value']})
    
    response = {
        "type" : "temp",
        "interval":"1h",
        "data":formatted_results
    }
    
    return jsonify(response)