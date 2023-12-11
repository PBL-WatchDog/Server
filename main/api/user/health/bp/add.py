from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query, numberutil, dateutil

from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point

from datetime import datetime, timedelta, timezone

from . import bp

@bp.route('/add', methods=['POST'])
@jwt_required()
def write_blood_pressure_data_tsdb():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400

    data = request.get_json()
    systolic = numberutil.to_int(data.get('systolic'))
    diastolic = numberutil.to_int(data.get('diastolic'))

    if not (systolic and diastolic): 
        return jsonify({"msg":"no data found in body"})
    
    if systolic < 0 or diastolic < 0:
        return jsonify({"msg":"invalid parameter range for systolic or diastolic"}), 400
    
    target_date = data.get('date', None)

    bucket = 'smarthome'

    point = Point("SensorData").tag("mac_address", gateway_id).tag("Device", "bp_meter")
    point.field("systolic", str(systolic)).field("diastolic", str(diastolic))

    if target_date:
        target_date = dateutil.get_datetime_by_utc_isoformat(target_date)
        if target_date > datetime.utcnow().replace(tzinfo=timezone.utc):
            return jsonify({"msg":"invalid parameter"}), 422
        point.time(target_date)

    write_api = influxDB_client.client.write_api(write_options=SYNCHRONOUS)
    write_api.write(bucket=bucket, record=point)

    return jsonify({"msg": "success"}), 200