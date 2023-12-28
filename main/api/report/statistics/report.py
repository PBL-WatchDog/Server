from flask import jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import permission
from main.utils import mysql_query
from main.config.config import origin_df

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
    
    response = {"msg":"success"}
    df = get_csv_data(gateway_id, ('2023-12-03 15:00', '2023-12-10 15:00'), ["temperature", "humidity"])

    temperature = df["temperature"]
    humidity = df["humidity"]

    max_temp_idx, min_temp_idx = temperature.idxmax(), temperature.idxmin() 
    max_temp, min_temp = temperature[max_temp_idx], temperature[min_temp_idx]

    max_humi_idx, min_humi_idx = humidity.idxmax(), humidity.idxmin() 
    max_humi, min_humi = humidity[max_humi_idx], humidity[min_humi_idx]
    
    data = {}
    data['temperature'] = {"max": [max_temp_idx, max_temp], "min": [min_temp_idx, min_temp]}
    data['humidity'] = {"max": [max_humi_idx, max_humi], "min": [min_humi_idx, min_humi]}

    response['data'] = data
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
  
