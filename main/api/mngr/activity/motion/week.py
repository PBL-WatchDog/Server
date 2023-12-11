from flask import jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import influx_query, mysql_query, dateutil

from datetime import datetime, timedelta

from . import motion, ON_FLAG, DEVICE_TYPE

@motion.route('/week', methods=["GET"])
@jwt_required()
def get_motion_by_week():
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
    times = influx_query.get_last_time_for_SensorData(gateway_id, device_list, "0500?00")
    
    response = {"msg":"success", "data":{}}
    most_start = None
    most_end = None
    most_full_time = timedelta(0)
    for device_id, end_time in times.items():
        start_time = end_time - timedelta(days=7)
        query = f"""
                from(bucket: "smarthome")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "SensorData")
                    |> filter(fn: (r) => r.mac_address == "{gateway_id}" and r.Device == "{device_id}" and r._field == "0500?00")
                    |> sort(columns: ["_time"], desc: false)
                """
        records = influxDB_client.fastQuery(query)
        
        prev_time = None
        full_time = timedelta(0)

        range_start = None
        range_end = None
        time = None
        value = None
        start = None
        end = None
        for record in records:
            value = record.get('_value')
            timeStr = record.get('_time')
            time = datetime(int(timeStr[:4]), int(timeStr[5:7]), int(timeStr[8:10]), int(timeStr[11:13]), int(timeStr[14:16]), int(timeStr[17:19]), int(timeStr[20:-1][:6]))

            if not start:
                range_start_str = record.get('_start')
                range_start = datetime(int(range_start_str[:4]), int(range_start_str[5:7]), int(range_start_str[8:10]), int(range_start_str[11:13]), int(range_start_str[14:16]), int(range_start_str[17:19]), int(range_start_str[20:-1][:6]))
                range_end_str = record.get('_stop')
                range_end = datetime(int(range_end_str[:4]), int(range_end_str[5:7]), int(range_end_str[8:10]), int(range_end_str[11:13]), int(range_end_str[14:16]), int(range_end_str[17:19]), int(range_end_str[20:-1][:6]))
                start = time
                if value not in ON_FLAG:
                    full_time += start - range_start

                if not most_start:
                    most_start = time

            if value in ON_FLAG:
                prev_time = time
            else:
                if prev_time:
                    full_time += time - prev_time
                prev_time = None

        end = time

        if value in ON_FLAG:
            full_time += range_end - end

        most_full_time += full_time
        response["data"][device_id] = {"time": int(full_time.total_seconds()), "range":{"start":dateutil.get_utc_isoformat(start), "end":dateutil.get_utc_isoformat(end)}}
    most_end = end
    response["range"] = {"start":dateutil.get_utc_isoformat(most_start), "end":dateutil.get_utc_isoformat(most_end)}
    response["time"] = int(most_full_time.total_seconds())
    return jsonify(response)