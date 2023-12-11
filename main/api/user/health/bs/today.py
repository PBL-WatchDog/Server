from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query, dateutil, numberutil

from datetime import datetime, timedelta, timezone

from . import bs
from ._figure import figure

@bs.route('/today', methods=['GET'])
@jwt_required()
def get_today_blood_sugar():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    offset = numberutil.to_int(request.args.get('offset', '0'))
    if offset is None:
        return jsonify({"msg":"invalid parameter"}), 422

    today = datetime.utcnow().replace(tzinfo=timezone.utc)
    today = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    start_time = dateutil.get_local_datetime(today, offset)
    end_time = start_time + timedelta(days=1)

    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
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
        data['bld_sugar'] = record.get('_value')
    
    data["figure"] = figure(data['bld_sugar'])
    
    return jsonify({"msg": "success", "data": data})