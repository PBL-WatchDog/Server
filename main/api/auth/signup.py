from . import auth, NAME_REGEX, PHONE_REGEX

from flask import request, jsonify
from mysql.connector import IntegrityError

from main.config import mysql_connector
import hashlib

@auth.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    phone = data.get("phone", '')
    name = data.get("name", '')
    email = "tmp@tmp.com"
    gateway_id = data.get("gw_id", '')
    password = data.get("password", '')
    
    if not (phone and name and gateway_id and password) or not (NAME_REGEX.match(name) and PHONE_REGEX.match(phone) and len(password) == 64):
        return jsonify({"msg":"invalid format"}), 422

    pw_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()

    try:
        sql = "INSERT INTO User (name, phone, email, password, gateway_id) VALUES (%s, %s, %s, %s, %s)"
        parmas = (name, phone, email, pw_hash, gateway_id)
        mysql_connector.sql_execute(sql, parmas)
        return jsonify({"msg":"success"})
    except IntegrityError as ex:
        return jsonify({"msg":"already registed user"}), 422