from flask import  jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import mysql_connector, permission

from . import device

# 등록 대기 중인 디바이스 목록 조회(pending device 테이블)
@device.route('/waiting', methods=['GET'])
@jwt_required()
def get_pending_device_list():
    user_id, auth, _ = get_jwt_identity().split(':')
    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    sql = "select * from PendingDevice where gateway_id = (select gateway_id from User where user_id = %s)"
    pending_device_list = mysql_connector.sql_execute(sql, (user_id,))

    if pending_device_list:
        response = {"msg" : "success"}
        response["data"] = pending_device_list
        return jsonify(response), 200
    else:
        return jsonify({"msg": "no registered pending devices"}), 204
    