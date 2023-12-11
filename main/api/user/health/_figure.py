
from main.config import influxDB_client

from .bp._figure import figure as bp_figure
from .bs._figure import figure as bs_figure
from .oxy._figure import figure as oxy_figure

from collections import defaultdict

state = ["good", "careful", "warning", "danger", "emergency"]

def figure(gateway_id, start_date_obj, end_date_obj):
    try:
        if type(gateway_id) is str:
            temp = None
            humi = None
            dew = None
            diastolic = None
            systolic = None
            bld_sugar = None
            spo2 = None
            bpm = None

            query = f"""from(bucket: "smarthome")
                        |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                        |> filter(fn: (r) => r.mac_address == "{gateway_id}")
                        |> filter(fn: (r) => r["Device"] == "bp_meter" or r["Device"] == "bs_meter" or r["Device"] == "oxymeter" or r["_field"] == "dew_point" or r["_field"] == "humidity" or r["_field"] == "temperature")
                        |> last()
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    """
            records = influxDB_client.fastQuery(query)
            for record in records:
                if record.get('temperature'): temp = float(record.get('temperature'))
                if record.get('humidity'): humi = float(record.get('humidity'))
                if record.get('dew_point'): dew = float(record.get('dew_point'))
                if record.get('diastolic'): diastolic = float(record.get('diastolic'))
                if record.get('systolic'): systolic = float(record.get('systolic'))
                if record.get('bld_sugar'): bld_sugar = float(record.get('bld_sugar'))
                if record.get('spo2'): spo2 = float(record.get('spo2'))
                if record.get('bpm'): bpm = float(record.get('bpm'))                    

            bp_state = bp_figure(systolic, diastolic)
            bs_state = bs_figure(bld_sugar)
            oxy_state = oxy_figure(spo2)

            return figure_by_data(bp_state, bs_state, oxy_state, temp)
        
        elif type(gateway_id) is list:
            gateway_ids_filter = ' '.join([f'r["mac_address"] == "{id}" or' for id in gateway_id])[:-3]

            query = f"""from(bucket: "smarthome")
                        |> range(start: {start_date_obj.isoformat()}, stop: {end_date_obj.isoformat()})
                        |> filter(fn: (r) => {gateway_ids_filter})
                        |> filter(fn: (r) => r["Device"] == "bp_meter" or r["Device"] == "bs_meter" or r["Device"] == "oxymeter" or r["_field"] == "dew_point" or r["_field"] == "humidity" or r["_field"] == "temperature")
                        |> last()
                        |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                    """
            
            data = defaultdict(dict)
            records = influxDB_client.fastQuery(query)
            for record in records:
                gateway_id = record.get('mac_address')
                target = data[gateway_id]

                if record.get('temperature'): target['temp'] = float(record.get('temperature'))
                if record.get('humidity'): target['humi'] = float(record.get('humidity'))
                if record.get('dew_point'): target['dew'] = float(record.get('dew_point'))
                if record.get('diastolic'): target['diastolic'] = float(record.get('diastolic'))
                if record.get('systolic'): target['systolic'] = float(record.get('systolic'))
                if record.get('bld_sugar'): target['bld_sugar'] = float(record.get('bld_sugar'))
                if record.get('spo2'): target['spo2'] = float(record.get('spo2'))
                if record.get('bpm'): target['bpm'] = float(record.get('bpm'))

            return {
                key : figure_by_data(
                    bp_figure(value.get('systolic'), value.get('diastolic')), 
                    bs_figure(value.get('bld_sugar')), 
                    oxy_figure(value.get('spo2')), 
                    value.get('temp', 20)
                ) for key, value in data.items()}
        
        return 0

    except Exception as ex:
        return 0
    
def figure_by_data(bp_state, bs_state, oxy_state, temp):
    """
     Args:
        bp_state (str): 혈압 상태 문자열 ["주의", "고혈압전", "수축기단독고혈압", "1기고혈압", "2기고혈압"] 중 하나

        bs_state (str): 혈당 상태 문자열 ["공복혈당장애", "저혈당증상", 당뇨병의심"] 중 하나

        oxy_state (str): 산소포화도 상태 문자열 ["저산소증주의", "저산소증위험", "매우위험"] 중 하나

        temp (float): 온도
    
    return:
        score (int): 위험도 점수 [0, 1, 2, 3, 4]
    """
    bp_score = 1 if bp_state == "주의" else \
               2 if bp_state == "고혈압전" else \
               3 if bp_state == "수축기단독고혈압" else \
               3 if bp_state == "1기고혈압" else \
               3 if bp_state == "2기고혈압" else \
               0
        
    bs_score = 1 if bs_state == "공복혈당장애" else \
               2 if bs_state == "저혈당증상" else \
               3 if bs_state == "당뇨병의심" else \
               0
    
    ox_score = 0 if oxy_state == "측정오류" else \
               1 if oxy_state == "저산소증주의" else \
               3 if oxy_state == "저산소증위험" else \
               3 if oxy_state == "매우위험" else \
               0
    
    temp_score = 3 if temp < 5 or temp > 39 else 0

    score_list = [bp_score, bs_score, ox_score, temp_score]
    
    score = max(score_list)

    score += 1 if score_list.count(3) > 1 else \
             1 if score_list.count(2) > 1 else \
             1 if score_list.count(3) == 0 and score_list.count(1) > 1 else \
             0
    
    return score
