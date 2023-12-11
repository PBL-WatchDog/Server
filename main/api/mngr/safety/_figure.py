from main.config import influxDB_client, permission
from main.utils import mysql_query

from collections import defaultdict

from .state import GAS_DECTECTOR_CLUSTER_ON_FLAG, GAS_DECTECTOR_CO_OFF_FLAG

def figure(gateway_ids):
    deviceInfo = mysql_query.get_deviceInfo_by_gatewwayIdList(gateway_ids, ["gas", "smoke"], True)
    gateway_ids_filter = ' '.join([f'r["mac_address"] == "{id}" or' for id in gateway_ids])[:-3].strip()
    smoke_device_ids_filter = ' '.join([f'r["Device"] == "{info.get("device_id")}" or' if info.get('device_type') == "smoke" else '' for info in deviceInfo])[:-3].strip()
    gas_device_ids_filter = ' '.join([f'r["Device"] == "{info.get("device_id")}" or' if info.get('device_type') == "gas" else ''  for info in deviceInfo])[:-3].strip()

    smoke_record = defaultdict(dict)
    gas_record = defaultdict(dict)
    if smoke_device_ids_filter:
        query = f"""
                from(bucket: "smarthome")
                    |> range(start:-1d)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => {gateway_ids_filter})
                    |> filter(fn: (r) => {smoke_device_ids_filter})
                    |> filter(fn: (r) => r["_field"] == "EF00/040E" or r["_field"] == "EF00/0401" or r["_field"] == "EF00/0104")
                    |> group(columns: ["_measurement", "_start", "_stop", "_time"], mode:"by")
                    |> sort(columns: ["_time"], desc: false)
                """
        records = influxDB_client.fastQuery(query)
        for record in records:
            gateway = smoke_record[record.get('mac_address')]
            device = record.get('Device')
            data = gateway.get(device, [])
            data.append({"_field":record.get("_field"), "_value":record.get("_value"), "_time":record.get("_time")})
            gateway[device] = data

        for smoke in smoke_record:
            gateway = smoke_record[smoke]
            for device in gateway:
                data = gateway[device]
                if len(data) > 1:
                    first, second = records[-2:]
                    if first.get('_field') in ['EF00/0401', 'EF00/0104'] and second.get('_field') == 'EF00/040E' \
                        and first.get('_value') == "1" and second.get('_value') == "2":
                        gateway[device] = True
                
                if data is not True:
                    gateway[device] = False
    
    if gas_device_ids_filter:
        query = f"""
                from(bucket: "smarthome")
                    |> range(start:-1d)
                    |> filter(fn: (r) => r["_measurement"] == "SensorData")
                    |> filter(fn: (r) => {gateway_ids_filter})
                    |> filter(fn: (r) => {gas_device_ids_filter})
                    |> filter(fn: (r) => r["_field"] == "0500?00" or r["_field"] == "CO")
                    |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    |> last(column: "_time")
                """
        records = influxDB_client.fastQuery(query)
        for record in records:
            gateway = gas_record[record.get('mac_address')]
            device = record.get('Device')
            gateway[device] = None
            cluster = record.get('0500?00')
            co = record.get('CO')
            if cluster == GAS_DECTECTOR_CLUSTER_ON_FLAG or co != GAS_DECTECTOR_CO_OFF_FLAG:
                gateway[device] = True

    result = {}
    for gateway_id in gateway_ids:
        smoke = smoke_record.get(gateway_id, {})
        smoke = any(smoke.values()) if smoke else None
        gas = gas_record.get(gateway_id, {})
        gas = any(gas.values()) if gas else None
        result[gateway_id] = check_values(smoke, gas)

    return result

def check_values(a, b):
    if (a is None and b is None):
        return None
    elif (a is False and b is False):
        return False
    else:
        return bool(a or b)