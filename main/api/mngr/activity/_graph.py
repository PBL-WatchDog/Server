from main.config import influxDB_client, mysql_connector
from main.utils import mysql_query, dateutil, influx_query

from datetime import datetime, timedelta, timezone
from collections import defaultdict

from .tv import ON_FLAG as TV_ON_FLAG
from .door import ON_FLAG as DOOR_ON_FLAG
from .motion import ON_FLAG as MOTION_ON_FLAG

DAY_OPTION = 7

def graph(gateway_ids, now):
    result = defaultdict(dict)

    deviceInfo = mysql_query.get_deviceInfo_by_gatewwayIdList(gateway_ids, ["door", "motion", "plug"], True)
    device_info_dict = defaultdict(dict)
    for info in deviceInfo:
        gateway_id = device_info_dict[info.get('gateway_id')]
        gateway_id[info.get('device_id')] = {'type':info.get('device_type'), 'loc':info.get('install_location')}
    gateway_ids_filter = ' '.join([f'r["mac_address"] == "{id}" or' for id in gateway_ids]).strip()[:-3]

    door_device_id = [info.get("device_id") for info in deviceInfo if info.get('device_type') == "door"]
    motion_device_id = [info.get("device_id") for info in deviceInfo if info.get('device_type') == "motion"]
    tv_device_id = [info.get("device_id") for info in deviceInfo if info.get('device_type') == "plug"]

    door_last_value = influx_query.get_last_value_for_SensorData_by_range([0, now.isoformat()], gateway_ids, door_device_id, "Contact")
    motion_last_value = influx_query.get_last_value_for_SensorData_by_range([0, now.isoformat()], gateway_ids, motion_device_id, "0500?00")
    tv_last_value = influx_query.get_last_value_for_SensorData_by_range([0, now.isoformat()], gateway_ids, tv_device_id, "ActivePower")

    door_device_ids_filter = ' '.join([f'r["Device"] == "{info}" or' for info in door_device_id]).strip()[:-3]
    motion_device_ids_filter = ' '.join([f'r["Device"] == "{info}" or' for info in motion_device_id]).strip()[:-3]
    plug_device_ids_filter = ' '.join([f'r["Device"] == "{info}" or' for info in tv_device_id]).strip()[:-3]
    

    if door_device_ids_filter:
        door_result = defaultdict(dict)
        query = f"""
                from(bucket: "smarthome")
                    |> range(start:-{DAY_OPTION}d)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => {gateway_ids_filter})
                    |> filter(fn: (r) => {door_device_ids_filter})
                    |> filter(fn: (r) => r["_field"] == "Contact")
                    |> sort(columns: ["_time"], desc: false)
                """
        door_records = influxDB_client.fastQuery(query)
        
        for record in door_records:
            gateway = door_result[record.get('mac_address')]
            device = record.get('Device')
            data = gateway.get(device, {})
            if not data:
                data['loc'] = device_info_dict.get(record.get('mac_address')).get(device, {}).get('loc', '')
                data['data'] = []
                gateway[device] = data
            data['data'].append({"_field":record.get("_field"), "_value":record.get("_value"), "_time":record.get("_time")})

        door_result = calc_door_and_motion_data(now, gateway_ids, door_result, door_last_value, [DOOR_ON_FLAG], 'door')
        for key in door_result:
            result[key].update(door_result[key])
            
    if motion_device_ids_filter:
        motion_result = defaultdict(dict)
        query = f"""
                from(bucket: "smarthome")
                    |> range(start:-{DAY_OPTION}d)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => {gateway_ids_filter})
                    |> filter(fn: (r) => {motion_device_ids_filter})
                    |> filter(fn: (r) => r["_field"] == "0500?00")
                    |> sort(columns: ["_time"], desc: false)
                """
        motion_records = influxDB_client.fastQuery(query)
        for record in motion_records:
            gateway = motion_result[record.get('mac_address')]
            device = record.get('Device')
            data = gateway.get(device, {})
            if not data:
                data['loc'] = device_info_dict.get(record.get('mac_address')).get(device, {}).get('loc', '')
                data['data'] = []
                gateway[device] = data
            data['data'].append({"_field":record.get("_field"), "_value":record.get("_value"), "_time":record.get("_time")})

        motion_result = calc_door_and_motion_data(now, gateway_ids, motion_result, motion_last_value, MOTION_ON_FLAG, 'motion')
        for key in motion_result:
            result[key].update(motion_result[key])

    if plug_device_ids_filter:
        plug_result = defaultdict(dict)
        query = f"""
                from(bucket: "smarthome")
                    |> range(start:-{DAY_OPTION}d)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => {gateway_ids_filter})
                    |> filter(fn: (r) => {plug_device_ids_filter})
                    |> filter(fn: (r) => r["_field"] == "ActivePower")
                    |> sort(columns: ["_time"], desc: false)
                """
        plug_records = influxDB_client.fastQuery(query)
        for record in plug_records:
            gateway = plug_result[record.get('mac_address')]
            device = record.get('Device')
            data = gateway.get(device, {})
            if not data:
                data['loc'] = device_info_dict.get(record.get('mac_address')).get(device, {}).get('loc', '')
                data['data'] = []
                gateway[device] = data
            data['data'].append({"_field":record.get("_field"), "_value":record.get("_value"), "_time":record.get("_time")})

        plug_result = calc_tv_data(now, gateway_ids, plug_result, tv_last_value)
        for key in plug_result:
            result[key].update(plug_result[key])


    return result

def calc_door_and_motion_data(now : datetime, gateway_ids, datas, last_values, ON_FLAG, type):
    result = defaultdict(dict)
    one_day = timedelta(days=1)
    now = datetime.utcnow().replace(tzinfo=timezone.utc)

    start_date_obj = now - timedelta(days=DAY_OPTION)
    start_standard_date_obj = datetime(start_date_obj.year, start_date_obj.month, start_date_obj.day, tzinfo=timezone.utc)
    days = dateutil.calculate_days(start_standard_date_obj, now, 0)
    
    for gateway_id in gateway_ids:
        devices = datas.get(gateway_id, {})
        result_gateway_id = result[gateway_id]
        for device in devices:
            records = devices[device]['data']
            last_value = last_values.get(gateway_id, {})

            data = [{"date":start_standard_date_obj + timedelta(days=i), "hour":0, "first":None, "last":None} for i in range(days)]
            prev_time = None
            for record in records:
                value = record.get('_value')
                timeStr = record.get('_time')
                time = datetime(int(timeStr[:4]), int(timeStr[5:7]), int(timeStr[8:10]), int(timeStr[11:13]), int(timeStr[14:16]), int(timeStr[17:19]), int(timeStr[20:-1][:6]), tzinfo=timezone.utc)
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
                s_date = start_standard_date_obj + timedelta(days=i)
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
                        if last_value.get(device) in ON_FLAG:
                            if s_date.year == now.year and s_date.month == now.month and s_date.day == now.day:
                                v["hour"] += timedelta(hours=now.hour, minutes=now.minute).total_seconds()
                            elif s_date < now:
                                v["hour"] = (one_day if now > e_date else now - s_date).total_seconds();
                    
                    if prev_last:
                        if s_date.year == now.year and s_date.month == now.month and s_date.day == now.day:
                            v["hour"] += timedelta(hours=now.hour, minutes=now.minute).total_seconds()
                            prev_last = False
                        elif s_date < now:
                            v["hour"] = (one_day if now > e_date else now - s_date).total_seconds();

                if last:
                    if last.get("value") == True:
                        last_date : datetime = last.get("date")
                        if last_date:
                            if s_date.year == now.year and s_date.month == now.month and s_date.day == now.day:
                                v["hour"] += (now - last_date).total_seconds()
                            elif e_date < now:
                                v["hour"] += ((e_date if e_date < now else now) - last_date).total_seconds()
                                prev_last = True
                            else:
                                v["hour"] += (now - last_date).total_seconds()
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
            
            result_gateway_id[device] = {"data" : data, "type" : type, "loc": devices[device]['loc']}

    return result


def calc_tv_data(now : datetime, gateway_ids, tv_datas, last_values):
    result = defaultdict(dict)

    most_first = False
    start_date_obj = now - timedelta(days=DAY_OPTION)
    start_standard_date_obj = datetime(start_date_obj.year, start_date_obj.month, start_date_obj.day, tzinfo=timezone.utc)

    days = dateutil.calculate_days(start_standard_date_obj, now, 0)

    for gateway_id in gateway_ids:
        devices = tv_datas.get(gateway_id, {})
        result_gateway_id = result[gateway_id]
        for device in devices:
            records = devices[device]['data']
            last_value = last_values.get(gateway_id, {})
            data = [{"date":start_standard_date_obj + timedelta(days=i), "hour":0, "first":None, "last":None} for i in range(days)]
            prev_time = None
            for record in records:
                value = float(record.get('_value', '0'))
                timeStr = record.get('_time')
                time = datetime(int(timeStr[:4]), int(timeStr[5:7]), int(timeStr[8:10]), int(timeStr[11:13]), int(timeStr[14:16]), int(timeStr[17:19]), int(timeStr[20:-1][:6]), tzinfo=timezone.utc)
                current_data = data[(time.date() - start_standard_date_obj.date()).days]

                if current_data.get("first") == None:
                    current_data["first"] = {"date":time, "value":value > TV_ON_FLAG}
                    prev_time = None

                if most_first and last_value and last_value.get(device):
                    if float(last_value.get(device)) > TV_ON_FLAG:
                        prev_time = start_date_obj
                    most_first = True
                
                current_data["last"] = {"date":time, "value":value > TV_ON_FLAG}

                if value > TV_ON_FLAG:
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

            result_gateway_id[device] = {'data' : data, "type":'plug', "loc": devices[device]['loc']}

    return result