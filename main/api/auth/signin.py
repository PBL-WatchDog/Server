from . import auth, ACCESS_EXPIRED, REFRESH_EXPIRED

from flask import request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token
from datetime import datetime

from main.config import mysql_connector
import hashlib

@auth.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()
    phone = data.get("phone", '')
    password = data.get("password", '')
    try:
        pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        sql = "SELECT user_id, name, auth FROM User WHERE phone=%s AND password=%s"
        parmas = (phone, pw_hash)
        result = mysql_connector.sql_execute(sql, parmas, True)
        
        if result:
            result = result[0]
            name = result['name']
            user_id_auth = f"{result['user_id']}:{result['auth']}:{name}"
            user_id_auth_auto_login = f"{result['user_id']}:{result['auth']}:{data.get('autologin', False)}:{name}"
            access_token = create_access_token(identity=user_id_auth, fresh=True, expires_delta=ACCESS_EXPIRED)  # identity 설정
            refresh_token = create_refresh_token(identity=user_id_auth_auto_login, expires_delta=REFRESH_EXPIRED)
            response = jsonify({'token': access_token, 'auth': str(result['auth']), "name":name})
            
            if data.get('autologin', False):
                response.set_cookie("refresh_token_cookie", value=refresh_token, secure=True, httponly=True, expires=datetime.now() + REFRESH_EXPIRED)
            else:
                response.set_cookie("refresh_token_cookie", value=refresh_token, secure=True, httponly=True)
                
            return response
        else:
            return jsonify({"msg":"login failed"}), 401
    except Exception as ex:
        print("Error:", ex)