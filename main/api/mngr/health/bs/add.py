from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query, numberutil, dateutil

from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import Point

from datetime import datetime, timedelta, timezone

from . import bs

@bs.route('/add', methods=['POST'])
@jwt_required()
def write_blood_sugar_data_tsdb():
    user_id, auth, _ = get_jwt_identity().split(':')
    
    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403

    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"invalid parameter"}), 422

    gateway_id = mysql_query.get_gateway_id_by_user_id(target_user_id, user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400

    data = request.get_json()
    bld_sugar = numberutil.to_int(data.get('bloodSugar'))

    if not bld_sugar:
        return jsonify({"msg":"no data found in body"})
    
    if bld_sugar < 0:
        return jsonify({"msg":"invalid parameter range for bld_sugar"}), 400

    target_date = data.get('date', None)

    bucket = 'smarthome'

    point = Point("SensorData").tag("mac_address", gateway_id).tag("Device", "bs_meter")
    point.field("bld_sugar", bld_sugar)

    if target_date:
        target_date = dateutil.get_datetime_by_utc_isoformat(target_date)
        if target_date > datetime.utcnow().replace(tzinfo=timezone.utc):
            return jsonify({"msg":"invalid parameter"}), 422
        point.time(target_date)

    write_api = influxDB_client.client.write_api(write_options=SYNCHRONOUS)
    write_api.write(bucket=bucket, record=point)

    return jsonify({"msg": "success"}), 200