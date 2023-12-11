from flask import Blueprint, jsonify, request
from main.config import influxDB_client, permission
from main.utils import influx_query, mysql_query, dateutil, numberutil
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta

from . import plug, ON_FLAG, DEVICE_TYPE

@plug.route('/range', methods=['GET'])
@jwt_required()
def get_tv_by_range():
    user_id, auth, _ = get_jwt_identity().split(':')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    offset = numberutil.to_int(request.args.get('offset', '0'))

    target_device = request.args.get('device')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)
    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    if offset is None:
        return jsonify({"msg":"invalid parameter"}), 422
    
    start_date_obj = dateutil.get_datetime_by_utc_isoformat(start_date)
    end_date_obj = dateutil.get_datetime_by_utc_isoformat(end_date)
    if not (start_date_obj and start_date_obj) or start_date_obj > end_date_obj:
        return jsonify({"msg":"invalid parameter"}), 422

    if not target_device:
        device_list = [device[0] for device in mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, "plug")]
        if not device_list:
            return jsonify({"msg":"no device"}), 204
        target_device = device_list[0]
    
    last_value = influx_query.get_last_value_for_SensorData_by_range([0, start_date_obj.isoformat()], gateway_id, [target_device], "ActivePower")
    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                |> filter(fn: (r) => r._measurement == "SensorData" and r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => r.Device == "{target_device}")
                |> filter(fn: (r) => r._field == "ActivePower")
            """
    
    records = influxDB_client.fastQuery(query)

    most_first = False
    start_standard_date_obj : datetime = dateutil.get_local_datetime(start_date_obj, offset)
    start_standard_date_obj = datetime(start_standard_date_obj.year, start_standard_date_obj.month, start_standard_date_obj.day, tzinfo=start_standard_date_obj.tzinfo)

    days = dateutil.calculate_days(start_date_obj, end_date_obj, offset)
    data = [{"date":start_standard_date_obj + timedelta(days=i), "hour":0, "first":None, "last":None} for i in range(days)]

    prev_time = None
    
    for record in records:
        value = float(record.get('_value', '0'))
        timeStr = record.get('_time')
        time = datetime(int(timeStr[:4]), int(timeStr[5:7]), int(timeStr[8:10]), int(timeStr[11:13]), int(timeStr[14:16]), int(timeStr[17:19]), int(timeStr[20:-1][:6]), tzinfo=timezone.utc)
        time = dateutil.get_local_datetime(time, offset)
        current_data = data[(time.date() - start_standard_date_obj.date()).days]

        if current_data.get("first") == None:
            current_data["first"] = {"date":time, "value":value > ON_FLAG}
            prev_time = None

        if most_first and last_value and last_value.get(target_device):
            if float(last_value.get(target_device)) > ON_FLAG:
                prev_time = start_date_obj
            most_first = True
        
        current_data["last"] = {"date":time, "value":value > ON_FLAG}

        if value > ON_FLAG:
            if prev_time:
                current_data["hour"] += (time - prev_time).total_seconds()
            prev_time = time
                    
        else:
            if prev_time:
                current_data["hour"] += (time - prev_time).total_seconds()
            prev_time = None
    
    for v in data:
        v["hour"] = int(v["hour"]) // 3600
        v["date"] = dateutil.get_utc_isoformat(v["date"])
        first = v.get("first")
        last = v.get("last")

        if first:
            first["date"] = dateutil.get_utc_isoformat(first["date"])
        
        if last:
            last["date"] = dateutil.get_utc_isoformat(last["date"])

    response = {
        "type" : "tv",
        "interval":"1d",
        "data":data,
        "prev" : 1 if last_value.get(target_device) and float(last_value.get(target_device)) > ON_FLAG else 0,
    }
    
    return jsonify(response)

