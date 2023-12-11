from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.utils import mysql_query
from main.config import mysql_connector, permission

from . import device

@device.route('/delete', methods=['DELETE'])
@jwt_required()
def delete_device():
    user_id, auth, _ = get_jwt_identity().split(':')
    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)
    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    device_id = request.args.get('device_id')
    if not device_id:
        return jsonify({"msg": "no device_id"}), 400;
    
    sql = "delete from Device where device_id = %s and gateway_id = %s"
    mysql_connector.sql_execute(sql, (device_id, gateway_id))
    return jsonify({"msg": "success"}), 200