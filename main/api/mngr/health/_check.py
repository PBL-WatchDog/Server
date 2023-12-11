from main.config import influxDB_client

def check(gateway_ids, start_date_obj, end_date_obj):
    gateway_ids_filter = ' '.join([f'r["mac_address"] == "{id}" or' for id in gateway_ids])[:-3].strip()

    query = f"""
            from(bucket: "smarthome")
                |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                |> filter(fn: (r) => r["_measurement"] == "SensorData")
                |> filter(fn: (r) => {gateway_ids_filter})
                |> filter(fn: (r) => r["Device"] == "bp_meter" or r["Device"] == "bs_meter" or r["Device"] == "oxymeter")
                |> last()
                |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """
    today_states = influxDB_client.fastQuery(query)
    today_states_dict = dict.fromkeys(gateway_ids, {'bp':False, 'bs':False, 'ox':False})
    for today_state in today_states:
        gateway_id = today_state.get('mac_address')
        today_state_dict = today_states_dict[gateway_id]

        if today_state.get('diastolic') and today_state.get('systolic'):
            today_state_dict['bp'] = True
        if today_state.get('bld_sugar'):
            today_state_dict['bs'] = True
        if today_state.get('spo2') and today_state.get('bpm'):
            today_state_dict['ox'] = True

    return today_states_dict