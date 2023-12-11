from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

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