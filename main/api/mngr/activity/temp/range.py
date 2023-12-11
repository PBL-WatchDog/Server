from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query

import json

from . import temp

@temp.route('/range', methods=['GET'])
@jwt_required(fresh=True)
def get_temperature_by_range():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403
    
    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"invalid parameter"}), 422

    gateway_id = mysql_query.get_gateway_id_by_user_id(target_user_id, user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400

    start_date = request.args.get('start')
    end_date = request.args.get('end')
    every = request.args.get('every', "1d")

    if not (start_date and end_date):
        return jsonify({"msg":"invalid parameter"}), 422
    
    query_api = influxDB_client.client.query_api()
    query = f"""
            import "json"

            from(bucket: "smarthome")
                |> range(start: {start_date}, stop: {end_date})
                |> filter(fn: (r) => r._measurement == "GatewayData" and r._field == "temperature" and r.mac_address == "{gateway_id}")
                |> window(every: {every})
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
        "interval":every,
        "data":formatted_results
    }
    
    return jsonify(response)