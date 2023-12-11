from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query, dateutil

from . import bp

@bp.route('/range', methods=['GET'])
@jwt_required()
def get_blood_pressure_by_range():
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
    
    tags = {'mac_address' : gateway_id, 'Device' : 'bp_meter'}
    query_string_tags = ' and '.join([f'r.{k}=="{v}"' for k,v in tags.items()])

    query_api = influxDB_client.client.query_api()
    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_date}, stop: {end_date})
                |> filter(fn: (r) => r._measurement == "SensorData" and {query_string_tags})
                |> filter(fn: (r) => r._field == "diastolic" or r._field == "systolic") 
                |> map(fn: (r) => ({"{"} r with _value: int(v: r._value) {"}"}))
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """
    result = None
    try:
        result = query_api.query_data_frame(query=query, org="Brighten").to_dict(orient = 'records')
    except:
        return jsonify({"msg":"invalid parameter"}), 422
    
    formatted_results = []
    for item in result:
        formatted_results.append({'date': dateutil.get_utc_isoformat(item['_time']), 'diastolic': item['diastolic'], 'systolic':item['systolic']})

    data = {
            "type" : "bp",
            "interval": every,   
            "data": formatted_results,
        }
    return jsonify(data)