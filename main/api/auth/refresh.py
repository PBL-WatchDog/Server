from . import auth, ACCESS_EXPIRED, REFRESH_EXPIRED

from flask import  jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from datetime import datetime

@auth.route('/refresh', methods=['GET'])
@jwt_required(refresh=True, locations=['cookies'])
def refresh():
    user_id, auth, autologin, name = get_jwt_identity().split(':')
    user_id_auth = f"{user_id}:{auth}:{name}"
    user_id_auth_auto_login = f"{user_id}:{auth}:{autologin}:{name}"

    access_token = create_access_token(identity=user_id_auth, fresh=True, expires_delta=ACCESS_EXPIRED)
    refresh_token = create_refresh_token(identity=user_id_auth_auto_login, expires_delta=REFRESH_EXPIRED)
    response = jsonify({'token': access_token, 'auth':auth, "name":name})
    
    if autologin:
        response.set_cookie("refresh_token_cookie", value=refresh_token, httponly=True, secure=True, expires=datetime.now() + REFRESH_EXPIRED)

    return response
    