from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import mysql_connector, permission

from . import device

# 사용자 gateway_id에 등록된 device 기기 전부 조회
@device.route('/list', methods=['GET'])
@jwt_required()
def get_device_list():
    _, auth, _ = get_jwt_identity().split(':')
    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403
    
    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"require user parameter"}), 400
    
    sql = "select device_id, device_type, install_location, reg_date from Device where gateway_id = (select gateway_id from User where user_id = %s)"
    device_list = mysql_connector.sql_execute(sql, (target_user_id,))

    if device_list:
        response = {"msg":"success"}
        response["data"] = device_list
        return jsonify(response)
    else:
        return jsonify({"msg": "no registered devices"}), 404