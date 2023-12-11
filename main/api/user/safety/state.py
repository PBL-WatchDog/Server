from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query

from . import safety

GAS_DECTECTOR_CLUSTER_ON_FLAG = "210000010000"
GAS_DECTECTOR_CO_OFF_FLAG = "0"

@safety.route('/state', methods=["GET"])
@jwt_required()
def get_safety_by_state():
    user_id, auth, _ = get_jwt_identity().split(':')
    
    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)
    
    if not gateway_id:
        return jsonify({"msg":"no data"}), 204 

    response = {"msg":"success"}

    # 연기 센서 확인
    smoke_device_ids = mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, "smoke")
    
    if smoke_device_ids:
        smoke_device_ids = dict(smoke_device_ids)
        smoke = False
        for smoke_device_id in smoke_device_ids:
            query = f"""
                    from(bucket: "smarthome")
                    |> range(start:-1d)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => r["mac_address"] == "{gateway_id}")
                    |> filter(fn: (r) => r["Device"] == "{smoke_device_id}")
                    |> filter(fn: (r) => r["_field"] == "EF00/040E" or r["_field"] == "EF00/0401" or r["_field"] == "EF00/0104")
                    |> group(columns: ["_measurement", "_start", "_stop", "_time"], mode:"by")
                    |> sort(columns: ["_time"], desc: false)
                    """
            records = influxDB_client.fastQuery(query)
            
            if len(records) > 1:
                first, second = records[-2:]
                if first.get('_field') in ['EF00/0401', 'EF00/0104'] and second.get('_field') == 'EF00/040E' \
                    and first.get('_value') == "1" and second.get('_value') == "2":
                    smoke |= True

        response["smoke"] = smoke

    gas_device_ids = mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, "gas")
    if gas_device_ids:
        gas = False
        for gas_device_id in gas_device_ids:
            query = f"""
                    from(bucket: "smarthome")
                    |> range(start:-1d)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => r["mac_address"] == "{gateway_id}")
                    |> filter(fn: (r) => r["Device"] == "{gas_device_id}")
                    |> filter(fn: (r) => r["_field"] == "0500?00" or r["_field"] == "CO")
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> last(column: "_time")
                    """
            records = influxDB_client.fastQuery(query)
            
            if len(records):
                cluster = records.get('0500?00')
                co = records.get('CO')
                if cluster == GAS_DECTECTOR_CLUSTER_ON_FLAG or co != GAS_DECTECTOR_CO_OFF_FLAG:
                    gas = True

        response["gas"] = gas

    return jsonify(response)