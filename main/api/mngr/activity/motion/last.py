from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query

from . import motion, ON_FLAG, DEVICE_TYPE

@motion.route('/last', methods=["GET"])
@jwt_required()
def get_motion_by_last():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403

    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"invalid parameter"}), 422

    gateway_id = mysql_query.get_gateway_id_by_user_id(target_user_id, user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400

    device_dic = mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, DEVICE_TYPE)
    if not device_dic:
        return jsonify({"msg":"no device"}), 204
    
    device_dic = dict(device_dic)
    device_ids_filter = ' '.join([f'r.Device == "{device}" or' for device in device_dic])[:-3]

    if not device_dic:
        return jsonify({"msg":"no device"}), 204
    
    response = {"msg":"success"}

    query = f"""
            from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}")
                |> filter(fn: (r) =>  r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => {device_ids_filter})
                |> filter(fn: (r) => r._field == "0500?00")
                |> last()
            """
    data = {}
    records = influxDB_client.fastQuery(query)
    for record in records:
        device_id = record.get("Device")
        if device_id:
            data[device_id] = [record.get("_value", "") in ON_FLAG, device_dic.get(device_id)]

    response["data"] = data
    return jsonify(response)