from flask import  jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import mysql_connector, permission

from . import device

@device.route('/waiting', methods=['GET'])
@jwt_required()
def get_pending_device_list():
    _, auth, _ = get_jwt_identity().split(':')
    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403
    
    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"require user parameter"}), 400
    
    sql = "select * from PendingDevice where gateway_id = (select gateway_id from User where user_id = %s)"
    pending_device_list = mysql_connector.sql_execute(sql, (target_user_id,))

    if pending_device_list:
        response = {"msg" : "success"}
        response["data"] = pending_device_list
        return jsonify(response), 200
    else:
        return jsonify({"msg": "no registered pending devices"}), 204
    