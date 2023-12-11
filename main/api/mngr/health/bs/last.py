from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query

from . import bs
from ....user.health.bs._figure import figure

@bs.route('/last', methods=['GET'])
@jwt_required()
def get_blood_sugar_by_last():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403

    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"invalid parameter"}), 422

    gateway_id = mysql_query.get_gateway_id_by_user_id(target_user_id, user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400

    query = f"""
            from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}" and r.Device == "bs_meter")
                |> filter(fn: (r) => r._field == "bld_sugar") 
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
        data['bld_sugar'] = record.get('bld_sugar')
    
    data["figure"] = figure(data['bld_sugar'])
    
    return jsonify({"msg": "success", "data": data})
