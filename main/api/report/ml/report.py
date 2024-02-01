from flask import jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import permission
from main.utils import mysql_query
from main.config.config import origin_df

from . import ml

import pandas as pd
import numpy as np
import os
from datetime import datetime, timezone

def get_csv_data(gateway_id, range, col):
    df = origin_df[origin_df['mac_address'] == gateway_id][range[0]:range[1]][col]
    return df

def create_sequences(data, sequence_length):
    xs = []
    ys = []
    for i in range(len(data) - sequence_length):
        xs.append(data[i:(i + sequence_length)])
        ys.append(data[i + sequence_length])
    return np.array(xs), np.array(ys)

@ml.route('/temperature', methods=["GET"])
@jwt_required()
def get_predict_temperature():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    try:
        # df = get_csv_data(gateway_id, ('2023-12-11', '2023-12-17'), ["temperature"])
        df = pd.read_csv(f'{os.getcwd()}/main/api/report/ml/{gateway_id}_temp.csv')
  
        INTERVAL = '1d'
        data = []
        time_list = []

        for idx, row in df.iterrows():
            date = row.date
            time = datetime(int(date[:4]), int(date[5:7]), int(date[8:10]), tzinfo=timezone.utc)
        
            data.append({"time": time, "value": row.temperature})
            time_list.append(time)

        response = {
            "msg":"success",
            "type": 'temp',
            "interval":INTERVAL,
            "time_list" : time_list,
            "data":data,
        }

        return jsonify(response)
    except Exception as ex:
        print(ex)
