from flask import jsonify
from main.config import influxDB_client, permission
from main.utils import influx_query, mysql_query, dateutil
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta, timezone

from . import plug, DEVICE_TYPE

@plug.route('/week', methods=['GET'])
@jwt_required()
def get_tv_by_week():
    user_id, auth, _ = get_jwt_identity().split(':')
    target_date = datetime(datetime.now().year, datetime.now().month, datetime.now().day, tzinfo=timezone.utc)

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)
    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    device_ids = [device[0] for device in mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, DEVICE_TYPE)]
    if not device_ids:
        return jsonify({"msg":"no device"}), 204
    device_ids_filter = ' '.join([f'r.Device == "{device}" or' for device in device_ids])[:-3]
    
    end_date_obj = target_date - timedelta(hours=9) # 시차 -9시간
    start_date_obj = end_date_obj - timedelta(days=7)

    INTERVAL = '6h'
    sub_string= '{ r with _value: if r._value == "" then 0.0 else float(v: r._value) }'
    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                |> timeShift(duration: 9h)
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => {device_ids_filter})
                |> filter(fn: (r) => r._field == "ActivePower")
                |> map(fn: (r) => ({sub_string}))
                |> aggregateWindow(every: {INTERVAL}, fn: sum, createEmpty: true)
                |> fill(column: "_value", value: 0.0)
            """
    
    data = {device_id : {} for device_id in device_ids}
    data['device'] = device_ids
    
    records = influxDB_client.fastQuery(query)
    count_dic = {device_id : 0 for device_id in device_ids}
    time_set = set()
    
    for record in records:
        device_id = record.get("Device")
        data[device_id].setdefault("range", []).append({"time": record.get("_time"), "value": float(record.get("_value"))})
        count_dic[device_id] += float(record.get("_value"))
        time_set.add(record.get("_time"))
    time_list = sorted(list(time_set))

    for key, val in count_dic.items():
        data[key]["count"] = val
        if val == 0:
            data[key]["range"] = []
            for time in time_list:
                data[key]["range"].append({"time": time, "value": 0})

    response = {
        "msg":"success",
        "type" : DEVICE_TYPE,
        "interval":INTERVAL,
        "time_list" : time_list,
        "data":data,
    }

    return jsonify(response)