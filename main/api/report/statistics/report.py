from flask import jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import permission
from main.utils import mysql_query
from main.config.config import origin_df
from main.config import influxDB_client

from . import statistics

import pandas as pd
import matplotlib.pyplot as plt
import os

from sklearn.preprocessing import MinMaxScaler

def get_csv_data(gateway_id, range, col):
    df = origin_df[origin_df['mac_address'] == gateway_id][range[0]:range[1]][col]
    return df

def create_and_save_activity_plot(df, mac_address):
    # 't'는 원본 데이터프레임을 가리킵니다.
    df['time'] = df.index.strftime('%H:%M')  # 날짜를 시간 형식으로 변환
    df['door'] = df['door1'] + df['door2']
    df['motion'] = df['motion1'] + df['motion2']

    # 날짜별로 그룹화하고 합계 계산
    df_re = df.groupby("time").sum()[['door', 'motion']]
    # 스케일링
    scaler = MinMaxScaler(feature_range=(1, 10))
    scaled_df = scaler.fit_transform(df_re)
    df_re = pd.DataFrame(scaled_df, columns=['door', 'motion'], index=df_re.index)

    plt.figure(figsize=(12,6))
    plt.title(f'{mac_address} - Activity by Time Zone')
    # 막대 너비 및 위치 설정
    bar_width = 0.35
    index = df_re.index
    n = len(index)
    bar1_position = range(n)
    bar2_position = [x + bar_width for x in bar1_position]

    plt.bar(bar1_position, df_re['door'], width=bar_width, label='Sum of Door')
    plt.bar(bar2_position, df_re['motion'], width=bar_width, label='Sum of Motion')
    plt.xticks([r + bar_width / 2 for r in range(n)], index)
    plt.legend()
    plt.savefig(f'{os.getcwd()}/main/api/report/statistics/image/{mac_address}_activity_plot.png')  # 이미지로 저장


def create_and_save_plug_plot(df, mac_address):
    df['time'] = df.index.strftime('%H:%M')  # 날짜를 시간 형식으로 변환
    df_re = df.groupby("time").sum()

    plt.figure(figsize=(12,6))
    plt.title(f'{mac_address} - Plug by Time Zone')
    # 막대 너비 및 위치 설정
    bar_width = 0.35
    index = df_re.index
    n = len(index)

    plt.plot(df_re, label='Sum of Plug(W)')
    plt.xticks([r + bar_width / 2 for r in range(n)], index)
    plt.legend()
    plt.savefig(f'{os.getcwd()}/main/api/report/statistics/image/{mac_address}_plug_plot.png')  # 이미지로 저장

@statistics.route('/environment', methods=["GET"])
@jwt_required()
def get_max_min_temp_humidity():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    # InfluxDB 쿼리 생성
    query_api = influxDB_client.client.query_api()
    query = f"""
            from(bucket: "smarthome")
            |> range(start: 2023-12-03T15:00:00.000Z, stop: 2023-12-10T15:00:00.000Z)
            |> filter(fn: (r) => r._measurement == "GatewayData" and (r._field == "temperature" or r._field == "humidity") and r.mac_address == "{gateway_id}")
            |> aggregateWindow(every: 3h, fn: mean, createEmpty: false)
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        """

    # 쿼리 실행 및 DataFrame으로 결과 받기
    df = query_api.query_data_frame(query, org="Brighten")
    if df.empty:
        return jsonify({"msg": "No data found"}), 404

    # df = get_csv_data(gateway_id, ('2023-12-03 15:00', '2023-12-10 15:00'), ["temperature", "humidity"])

    # '_time' 컬럼을 datetime으로 변환
    df['_time'] = pd.to_datetime(df['_time'])

    # 온도와 습도의 최대값 및 최소값 찾기
    max_temp = df['temperature'].max()
    min_temp = df['temperature'].min()
    max_humi = df['humidity'].max()
    min_humi = df['humidity'].min()

    # 최대 및 최소값에 해당하는 시간 찾기 및 형식 변환
    # 최대 및 최소값에 해당하는 시간 찾기 및 형식 변환
    max_temp_time = df[df['temperature'] == max_temp]['_time'].iloc[0].strftime('%a, %d %b %Y %H:%M:%S GMT')
    min_temp_time = df[df['temperature'] == min_temp]['_time'].iloc[0].strftime('%a, %d %b %Y %H:%M:%S GMT')
    max_humi_time = df[df['humidity'] == max_humi]['_time'].iloc[0].strftime('%a, %d %b %Y %H:%M:%S GMT')
    min_humi_time = df[df['humidity'] == min_humi]['_time'].iloc[0].strftime('%a, %d %b %Y %H:%M:%S GMT')


    # 결과 데이터 구성
    data = {
        'temperature': {
            "max": {"time": max_temp_time, "value": max_temp},
            "min": {"time": min_temp_time, "value": min_temp}
        },
        'humidity': {
            "max": {"time": max_humi_time, "value": max_humi},
            "min": {"time": min_humi_time, "value": min_humi}
        }
    }

    response = {
        "msg": "success",
        "data": data
    }
    return jsonify(response)

@statistics.route('/acitvity', methods=["GET"])
@jwt_required()
def get_avg_activity():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    df = get_csv_data(gateway_id, ('2023-12-03 15:00', '2023-12-10 15:00'), ["door1", "door2", "motion1", "motion2"])
    create_and_save_activity_plot(df, gateway_id)  # 데이터 프레임 'df_re'를 함수에 전달
    filename = f'{os.getcwd()}/main/api/report/statistics/image/{gateway_id}_activity_plot.png'
    return send_file(filename, mimetype='image/png'), 200


@statistics.route('/plug', methods=["GET"])
@jwt_required()
def get_avg_plug():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    df = get_csv_data(gateway_id, ('2023-12-03 15:00', '2023-12-10 15:00'), ["plug"])
    create_and_save_plug_plot(df, gateway_id)  # 데이터 프레임 'df_re'를 함수에 전달
    filename = f'{os.getcwd()}/main/api/report/statistics/image/{gateway_id}_plug_plot.png'
    return send_file(filename, mimetype='image/png'), 200
  
