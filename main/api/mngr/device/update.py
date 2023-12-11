from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import mysql_connector, permission

from . import device

@device.route('/update', methods=['PATCH'])
@jwt_required()
def update_device_install_location():
    _, auth, _ = get_jwt_identity().split(':')
    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403
    
    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"require user parameter"}), 400
    
    data = request.get_json()
    device_id = data.get('device_id', '')
    install_location = data.get('install_location', '')
    if not device_id or not install_location:
        return jsonify({"msg": "no device_id or install_location body"}), 400;

    parmas = (install_location, device_id, target_user_id)
    sql = "update Device set install_location = %s where device_id = %s and gateway_id = (select gateway_id from User where user_id = %s)"
    mysql_connector.sql_execute(sql, parmas)
    return jsonify({"msg": "success"}), 200