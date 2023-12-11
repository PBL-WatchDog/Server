"""
자주쓰는 influx 2.0 쿼리 모듈화
"""

from main.config import influxDB_client

def get_deivce_id_list(gateway_id, model_id):
    """
    게이트웨이 명과, 모델 명을 이용해서 게이트웨이에 등록된 디바이스 번호(ex: 0x5D36) 리스트를 리턴
    :param gateway_id : "W220_818FB4"
    :param model_id : "RH3001"
    """
    query_api = influxDB_client.client.query_api()
    query = f"""
            from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "SensorData")
                |> filter(fn: (r) => r.mac_address == "{gateway_id}" and r._field == "ModelId" and r._value == "{model_id}")
                |> group(columns: ["ModelId"])
                |> last()
                |> distinct(column: "Device")
            """

    device_ids = []
    tables = query_api.query(query, org="Brighten")
    for table in tables:
        for record in table.records:
            device_ids.append(record.get_value())
    return device_ids

def get_last_time_for_SensorData(gateway_id, devices, field):
    """
    게이트웨이 명과, 디바이스 명, 필드 명을 이용해서 가장 마지막에 등록된 시간을 디바이스 별 리턴
    :param gateway_id : "W220_818FB4"
    :param devices : ["0x5D36"]
    :param field : "0500?00"
    """
    query_api = influxDB_client.client.query_api()
    filter_cond = 'r.Device == "' + '" or r.Device == "'.join(devices) + '"'
    query = f"""
            from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "SensorData")
                |> filter(fn: (r) => r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => {filter_cond})
                |> filter(fn: (r) => r._field == "{field}")
                |> last()
            """
    times = {}
    tables = query_api.query(query, org="Brighten")
    for table in tables:
        for record in table.records:
            times[record["Device"]] = record.get_time()
    
    return times

def get_last_value_for_SensorData_by_range(range, gateway_id, devices, field):
    """
    범위와, 게이트웨이 명과, 디바이스 명, 필드 명을 이용해서 가장 마지막에 등록된 시간을 디바이스 별 리턴
    :param range : ["2023-10-01T00:00:00Z", "2023-10-01T00:00:00Z"]
    :param gateway_id : "W220_818FB4"
    :param devices : ["0x5D36"]
    :param field : "0500?00"
    """
    query_api = influxDB_client.client.query_api()
    filter_cond = 'r.Device == "' + '" or r.Device == "'.join(devices) + '"'
    query = f"""
            from(bucket: "smarthome")
                |> range(start: {range[0]}, stop: {range[1]})
                |> filter(fn: (r) => r._measurement == "SensorData")
                |> filter(fn: (r) => r.mac_address == "{gateway_id}")
                |> filter(fn: (r) => {filter_cond})
                |> filter(fn: (r) => r._field == "{field}")
                |> last()
            """
    values = {}
    tables = query_api.query(query, org="Brighten")
    for table in tables:
        for record in table.records:
            values[record["Device"]] = record.get_value()
    
    return values

def get_all_last_value_for_SensorData_by_range(range, gateway_id, devices, field):
    """
    범위와, 게이트웨이 명과, 디바이스 명, 필드 명을 이용해서 가장 마지막에 등록된 시간을 디바이스 별 리턴
    :param range : ["2023-10-01T00:00:00Z", "2023-10-01T00:00:00Z"]
    :param gateway_id : ["W220_818FB4"]
    :param devices : ["0x5D36"]
    :param field : "0500?00"
    """
    query_api = influxDB_client.client.query_api()
    gateway_ids_filter = ' '.join([f'r.mac_address == "{id}" or' for id in gateway_id]).strip()[:-3]
    filter_cond = 'r.Device == "' + '" or r.Device == "'.join(devices) + '"'
    query = f"""
            from(bucket: "smarthome")
                |> range(start: {range[0]}, stop: {range[1]})
                |> filter(fn: (r) => r._measurement == "SensorData")
                |> filter(fn: (r) => {gateway_ids_filter})
                |> filter(fn: (r) => {filter_cond})
                |> filter(fn: (r) => r._field == "{field}")
                |> last()
            """
    values = {}
    tables = query_api.query(query, org="Brighten")
    for table in tables:
        data = {}
        address = None
        for record in table.records:
            if not address:
                address = record.get('mac_address')
            data[record["Device"]] = record.get_value()

        if address:
            values[address] = data
    
    return values