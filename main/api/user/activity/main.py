from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import requests, json

from main.config import influxDB_client, permission
from main.utils import mysql_query, dateutil

from . import activity

@activity.route('/main', methods=['GET'])
@jwt_required()
def get_main_by_recent():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403

    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    query_api = influxDB_client.client.query_api()
    query = f"""from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "GatewayData") 
                |> filter(fn: (r) => r.mac_address == "{gateway_id}")
                |> last()"""
    tables = query_api.query(query, org="Brighten")
    
    result = {}
    for table in tables:
        for record in table.records:
            if record.get_field() not in result:
                result[record.get_field()] = {
                    'time': dateutil.get_utc_isoformat(record.get_time()),
                    'value': record.get_value()
                }

    return jsonify(result)

friend_url = "https://kapi.kakao.com/v1/api/talk/friends"
send_url = "https://kapi.kakao.com/v1/api/talk/friends/message/send"
template_id = 101764

#발급받은 액세스 토큰 열어 저장.
with open("/home/smarthome/service-deploy/PBL_Server/main/config/kakao.json", "r") as fp: #파일 위치 확인 필요
    tokens = json.load(fp)

@activity.route('/kakao', methods=['GET'])
# @jwt_required()
def send_kakao_message():
    name ="김두현"
    link = "http://211.57.200.6:3333/main/report"
    try:
        # 친구 목록 조회
        headers = {"Authorization": "Bearer " + tokens["access_token"]}
        result = json.loads(requests.get(friend_url, headers=headers).text)
        print(result)
        friends_list = result.get("elements")
        friend_id = friends_list[1].get("uuid")
        # print(result)
        # 템플릿 전송 요청
        data = {
            "receiver_uuids": json.dumps([friend_id]),  # 수정된 부분
            "template_id": template_id,  # 템플릿 ID 추가
            "template_args": json.dumps({"name": name, "link": link}),  # 템플릿에 전달할 인자
        }
        response = requests.post(send_url, headers=headers, data=data)
        result = json.loads(response.text)
        return jsonify(result)
    except Exception as ex:
        print(ex)