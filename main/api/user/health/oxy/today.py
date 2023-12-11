from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query, numberutil, dateutil

from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point

from datetime import datetime, timedelta, timezone

from . import oxy
from ._figure import figure

@oxy.route('/today', methods=['GET'])
@jwt_required()
def get_today_oxymeter():
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
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}" and r.Device == "oxymeter")
                |> filter(fn: (r) => r._field == "spo2" or r._field == "bpm") 
                |> last() 
                |> map(fn: (r) => ({"{"} r with _value: int(v: r._value) {"}"}))
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """
    
    data = {}
    records = influxDB_client.fastQuery(query)

    if not records:
        return jsonify({'msg': 'no data'}), 204

    for record in records:
        data['spo2'] = record.get('spo2')
        data['bpm'] = record.get('bpm')
    
    data['figure'] = figure(data['spo2'])
    
    return jsonify({"msg": "success", "data": data})