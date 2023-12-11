from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from main.config import influxDB_client, permission
from main.utils import mysql_query

from . import temp

@temp.route('/last', methods=["GET"])
@jwt_required()
def get_temperature_by_last():
    user_id, auth, _ = get_jwt_identity().split(':')

    if auth != permission.PER_USER:
        return jsonify({"msg":"not eligible for access"}), 403
    
    gateway_id = mysql_query.get_gateway_id_by_user_id(user_id)

    if not gateway_id:
        return jsonify({"msg":"not found gateway"}), 400
    
    query_api = influxDB_client.client.query_api()
    query = f"""
            from(bucket: "smarthome")
                |> range(start: 0)
                |> filter(fn: (r) => r._measurement == "GatewayData")
                |> filter(fn: (r) => r.mac_address == "{gateway_id}" and r._field == "temperature")
                |> last()
            """

    response = {}
    tables = query_api.query(query, org="Brighten")
    for table in tables:
        for record in table.records:
            response = {
                'time': record.get_time(),
                'value': record.get_value(),
            }
            break

    return jsonify(response)