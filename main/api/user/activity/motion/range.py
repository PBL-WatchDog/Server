from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import influx_query, mysql_query, dateutil, numberutil

from datetime import datetime, timezone, timedelta

from . import motion, ON_FLAG, DEVICE_TYPE

@motion.route('/range', methods=["GET"])
@jwt_required()
def get_motion_by_range():
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
        device_ids = mysql_query.get_deviceInfo_by_gatewwayId(gateway_id, DEVICE_TYPE)
        if not len(device_ids) or not len(device_ids[0]): return jsonify({"msg":"no data"}), 204
        target_device = device_ids[0][0]
    
    last_value = influx_query.get_last_value_for_SensorData_by_range([0, start_date_obj.isoformat()], gateway_id, [target_device], "0500?00")
    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                |> filter(fn: (r) => r._measurement == "SensorData")
                |> filter(fn: (r) => r.mac_address == "{gateway_id}" and r.Device == "{target_device}" and r._field == "0500?00")
                |> sort(columns: ["_time"], desc: false)
            """

    records = influxDB_client.fastQuery(query)
    
    one_day = timedelta(days=1)
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    start_standard_date_obj : datetime = dateutil.get_local_datetime(start_date_obj, offset)
    start_standard_date_obj = datetime(start_standard_date_obj.year, start_standard_date_obj.month, start_standard_date_obj.day).astimezone(start_standard_date_obj.tzinfo)
    days = dateutil.calculate_days(start_date_obj, end_date_obj, offset)
    data = [{"date":start_standard_date_obj + timedelta(days=i), "hour":0, "first":None, "last":None} for i in range(days)]

    prev_time = None
    for record in records:
        value = record.get('_value')
        timeStr = record.get('_time')
        time = datetime(int(timeStr[:4]), int(timeStr[5:7]), int(timeStr[8:10]), int(timeStr[11:13]), int(timeStr[14:16]), int(timeStr[17:19]), int(timeStr[20:-1][:6]), tzinfo=timezone.utc)
        time = dateutil.get_local_datetime(time, offset)
        current_data = data[(time.date() - start_standard_date_obj.date()).days]

        if current_data.get("first") == None:
            current_data["first"] = {"date":time, "value":value in ON_FLAG}
            prev_time = None
        
        current_data["last"] = {"date":time, "value":value in ON_FLAG}

        if value in ON_FLAG:
            prev_time = time
                    
        else:
            if prev_time:
                current_data["hour"] += (time - prev_time).total_seconds()
            prev_time = None
    
    prev_first = None
    prev_last = None
    for i, v in enumerate(data):
        s_date = start_standard_date_obj.astimezone(timezone.utc) + timedelta(days=i)
        e_date = s_date + one_day
        first = v.get("first")
        last = v.get("last")


        if first:
            if first.get("value") == True:
                prev_first = True
            else:
                first_date : datetime = first.get("date")
                prev_first = False
                if first_date:
                    v["hour"] += (first_date - s_date).total_seconds()
        else:
            if prev_first is None:
                if last_value.get(target_device) in ON_FLAG:
                    if s_date.year == now.year and s_date.month == now.month and s_date.day == now.day:
                        v["hour"] += timedelta(hours=now.hour, minutes=now.minute).total_seconds()
                    elif s_date < now:
                        v["hour"] = (one_day if now > e_date else now - s_date).total_seconds()
                        
            if prev_last:
                if s_date.year == now.year and s_date.month == now.month and s_date.day == now.day:
                    v["hour"] += timedelta(hours=now.hour, minutes=now.minute).total_seconds()
                    prev_last = False
                elif s_date < now:
                    v["hour"] = (one_day if now > e_date else now - s_date).total_seconds()

        if last:
            if last.get("value") == True:
                last_date : datetime = last.get("date")
                if last_date:
                    if s_date.year == now.year and s_date.month == now.month and s_date.day == now.day:
                        v["hour"] += (now - last_date).total_seconds()
                    elif e_date < end_date_obj:
                        v["hour"] += ((e_date if e_date < now else now) - last_date).total_seconds()
                        prev_last = True
                    else:
                        v["hour"] += (end_date_obj - last_date).total_seconds()
                        prev_last = True
            else:
                prev_last = False

        v["hour"] = int(v["hour"]) // 3600
    
    for v in data:
        v["date"] = dateutil.get_utc_isoformat(v["date"])
        first = v.get("first")
        last = v.get("last")

        if first:
            first["date"] = dateutil.get_utc_isoformat(first["date"])
        
        if last:
            last["date"] = dateutil.get_utc_isoformat(last["date"])
    
    response = {
        "type" : "motion",
        "interval":"1d",
        "data":data
    }

    return jsonify(response)