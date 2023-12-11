from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from collections import defaultdict

from main.config import influxDB_client, permission
from main.utils import mysql_query

from . import safety, GAS_DECTECTOR_CLUSTER_ON_FLAG, GAS_DECTECTOR_CO_OFF_FLAG

@safety.route('/list', methods=["GET"])
@jwt_required()
def get_safety_by_list():
    user_id, auth, _ = get_jwt_identity().split(':')
    
    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403
    
    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"invalid parameter"}), 422

    target_device_type = request.args.get('type')
    if not target_device_type: return jsonify({"msg":"invalid parameter"}), 422

    gateway_id = mysql_query.get_gateway_id_by_user_id(target_user_id, user_id)
    
    if not gateway_id:
        return jsonify({"msg":"no data"}), 204 
    
    device_ids = mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, target_device_type)
    if not device_ids:
        return jsonify({"msg":"no data"}), 204 
    device_ids = dict(device_ids)

    response = {"msg":"success", target_device_type : []}

    device_filter = ' '.join([f'r["Device"] == "{id}" or' for id in device_ids])[:-3].strip()
    if target_device_type == "gas":
        query = f"""
                from(bucket: "smarthome")
                    |> range(start: 0)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => r["mac_address"] == "{gateway_id}")
                    |> filter(fn: (r) => {device_filter})
                    |> filter(fn: (r) => r["_field"] == "CO" or r["_field"] == "0500?00")
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> filter(fn: (r) => r["0500?00"] == "{GAS_DECTECTOR_CLUSTER_ON_FLAG}" or r["CO"] != "{GAS_DECTECTOR_CO_OFF_FLAG}")
                    |> sort(columns: ["_time"], desc: false)
                    """
        records = influxDB_client.fastQuery(query)
        response[target_device_type] = [record.get('_time') for record in records]

    elif target_device_type == "smoke":
        state = defaultdict(bool)
        query = f"""
                from(bucket: "smarthome")
                    |> range(start: 0)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => r["mac_address"] == "{gateway_id}")
                    |> filter(fn: (r) => {device_filter})
                    |> filter(fn: (r) => r["_field"] == "EF00/040E" or r["_field"] == "EF00/0401" or r["_field"] == "EF00/0104")
                    |> group(columns: ["_measurement", "_start", "_stop", "_time"], mode:"by")
                    |> sort(columns: ["_time"], desc: false)
                """
        records = influxDB_client.fastQuery(query)
        for record in records:
            if record.get('_field') in ['EF00/0401', 'EF00/0104'] and record.get('_value') == "1":
                state[record.get('Device')] = True
            
            elif record.get('_field') == 'EF00/040E' and record.get('_value') == "2":
                device_state = state[record.get('Device')]
                if device_state:
                    response[target_device_type].append(record.get('_time'))
                    state[record.get('Device')] = False
            else:
                state[record.get('Device')] = False


    return jsonify(response)