from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import mysql_connector, permission
from mysql.connector import IntegrityError

from . import device

@device.route('/new', methods=['POST'])
@jwt_required() 
def create_device():
    _, auth, _ = get_jwt_identity().split(':')
    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    data = request.get_json()
    device_id = data.get('device_id', '')
    device_type = data.get('device_type', '')
    gateway_id = data.get('gateway_id', '')
    install_location = data.get('install_location', '')

    if device_id and device_type and gateway_id:
        parmas = (device_id, device_type, gateway_id, install_location)
        sql = "insert into Device(device_id, device_type, gateway_id, install_location) Values(%s, %s, %s, %s)"
        try:
            mysql_connector.sql_execute(sql, parmas)
        except IntegrityError:
            return jsonify({"msg":"already registed device"}), 422

        parmas = (device_id, )
        sql = "delete from PendingDevice where device_id = %s"
        mysql_connector.sql_execute(sql, parmas)
        return jsonify({"msg": "success"})
    else:
        return jsonify({"msg": "missing required parameter"}), 400