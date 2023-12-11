from flask import jsonify
from main.config import influxDB_client, permission
from main.utils import mysql_query
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import plug, ON_FLAG, DEVICE_TYPE

@plug.route('/last', methods=['GET'])
@jwt_required()
def get_tv_by_state():
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
    
    response = {"msg":"success"}

    query = f"""
            from(bucket: "smarthome")
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => {device_ids_filter})
                |> filter(fn: (r) => r._field == "Power")
            """
    data = {}
    records = influxDB_client.fastQuery(query)
    for device_id in device_dic:
        data[device_id] = [False, device_dic[device_id]]

    for record in records:
            if record:
                print(record)
                data[record.get("Device")] = [record.get("_value") == "1", device_dic.get(device_id)]
    response["data"] = data
    return jsonify(response)