from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query

from . import bp
from ._figure import figure

@bp.route('/last', methods=['GET'])
@jwt_required()
def get_blood_pressure_by_last():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    query = f"""
            from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}" and r.Device == "bp_meter")
                |> filter(fn: (r) => r._field == "diastolic" or r._field == "systolic") 
                |> last() 
                |> map(fn: (r) => ({"{"} r with _value: int(v: r._value) {"}"}))
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """
    
    data = {}
    records = influxDB_client.fastQuery(query)
    
    if not records:
        return jsonify({'msg': 'no data'}), 204

    for record in records:
        data["time"] = record.get('_time')
        data['diastolic'] = record.get('diastolic')
        data['systolic'] = record.get('systolic')

    data["figure"] = figure(data['systolic'], data['diastolic'])
    
    return jsonify({"msg": "success", "data": data})
