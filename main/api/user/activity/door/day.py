from flask import jsonify, request

from main.config import influxDB_client, permission
from main.utils import mysql_query
from flask_jwt_extended import jwt_required, get_jwt_identity

from datetime import datetime, timezone, timedelta

from . import door, DEVICE_TYPE

@door.route('/day', methods=["GET"])
@jwt_required()
def get_door_by_day():
    user_id, auth, _ = get_jwt_identity().split(':')
    target_date = request.args.get('date')
    target_device = request.args.get('device')
    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)
    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    try:
        end_date_obj = datetime(int(target_date[:4]), int(target_date[5:7]), int(target_date[8:10]), tzinfo=timezone.utc) - timedelta(hours=9) # 시차 -9시간
        start_date_obj = end_date_obj - timedelta(days=1) 
    except Exception as ex:
        return jsonify({"msg":"invalid parameter"}), 422

    INTERVAL = '2h'
    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                |> timeShift(duration: 9h)
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => r.Device == "{target_device}")
                |> filter(fn: (r) => r._field == "Contact")
                |> aggregateWindow(every: {INTERVAL}, fn: count, createEmpty: true)
                |> keep(columns: ["_time", "Device", "_value"])
                |> fill(column: "_value", value: 0)
            """
    
    data = []

    records = influxDB_client.fastQuery(query)
    count = 0
    time_set = set()

    for record in records:
        data.append({"time": record.get("_time"), "value": int(record.get("_value"))})
        count += int(record.get("_value"))
        time_set.add(record.get("_time"))
    time_list = sorted(list(time_set))
    # for key, val in count_dic.items():
    #     data[key]["count"] = val
    #     if val == 0:
    #         data[key]["range"] = []
    #         for time in time_list:
    #             data[key]["range"].append({"time": time, "value": 0})

    response = {
        "msg":"success",
        "type" : DEVICE_TYPE,
        "interval":INTERVAL,
        "time_list" : time_list,
        "count": count,
        "data":data,
    }

    return jsonify(response)
   
    

