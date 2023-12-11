from flask import jsonify, request
from main.config import influxDB_client, permission
from main.utils import influx_query, mysql_query, dateutil
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

from . import tv, ON_FLAG, DEVICE_TYPE

@tv.route('/week', methods=['GET'])
@jwt_required()
def get_tv_by_week():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_ADMIN:
        return jsonify({"msg":"not eligible for access"}), 403

    target_user_id = request.args.get('user')
    if not target_user_id: return jsonify({"msg":"invalid parameter"}), 422

    gateway_id = mysql_query.get_gateway_id_by_user_id(target_user_id, user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400

    device_list = mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, DEVICE_TYPE)
    if not device_list:
        return jsonify({"msg":"no device"}), 204

    device_list = [device[0] for device in device_list]

    if not device_list:
        return jsonify({"msg":"no device"}), 204
    times = influx_query.get_last_time_for_SensorData(gateway_id, device_list, "ActivePower")

    response = {"msg":"success", "data":[]}
    most_start = None
    most_end = None
    start = None
    end = None
    most_full_time = timedelta(0)

    for device, end_time in times.items():
        start_time = end_time - timedelta(days=7)
        query = f"""
                from(bucket: "smarthome")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}" and r.Device == "{device}")
                    |> filter(fn: (r) => r._field == "ActivePower")
                    |> sort(columns: ["_time"], desc: false)
                """ 
        
        records = influxDB_client.fastQuery(query)

        prev_value = None
        prev_time = None
        full_time = timedelta(0)

        start = None
        end = None

        for record in records:
            value = float(record.get('_value', '0'))
            timeStr = record.get('_time')
            time = datetime(int(timeStr[:4]), int(timeStr[5:7]), int(timeStr[8:10]), int(timeStr[11:13]), int(timeStr[14:16]), int(timeStr[17:19]), int(timeStr[20:-1][:6]))

            if not start:
                start = time
                if not most_start:
                    most_start = time

            if prev_value:
                if value > ON_FLAG:
                    full_time += time - prev_time
                else: 
                    prev_value = None

            if value > ON_FLAG: 
                prev_value = ON_FLAG
            
            prev_time = time

        end = prev_time

        response["data"].append({"device":device, "time": int(full_time.total_seconds()), "range":{"start":dateutil.get_utc_isoformat(start), "end":dateutil.get_utc_isoformat(end)}})
        most_full_time += full_time
    
    most_end = end
    response["range"] = {"start":dateutil.get_utc_isoformat(most_start), "end":dateutil.get_utc_isoformat(most_end)}
    response["time"] = int(most_full_time.total_seconds())

    return jsonify(response)