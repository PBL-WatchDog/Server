from flask import jsonify

from main.config import influxDB_client, permission
from main.utils import mysql_query
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import door, ON_FLAG, DEVICE_TYPE

@door.route('/last', methods=["GET"])
@jwt_required()
def get_door_by_last():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400

    device_dic = mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, DEVICE_TYPE)
    if not device_dic:
        return jsonify({"msg":"no device"}), 204
    
    device_dic = dict(device_dic)
    device_ids_filter = ' '.join([f'r.Device == "{device}" or' for device in device_dic])[:-3]

    if not device_dic:
        return jsonify({"msg":"no device"}), 404
    
    response = {"msg":"success"}

    query = f"""
            from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "SensorData")
                |> filter(fn: (r) =>  r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => {device_ids_filter})
                |> filter(fn: (r) => r._field == "Contact")
                |> keep(columns: ["_time", "Device", "_value"])
                |> last()
            """
    data = {}
    records = influxDB_client.fastQuery(query)
    for record in records:
        if record.get("Device"):
            device_id = record.get("Device")
            data[device_id] = [record.get("_value") == ON_FLAG, device_dic.get(device_id)]

    response["data"] = data
    return jsonify(response)
