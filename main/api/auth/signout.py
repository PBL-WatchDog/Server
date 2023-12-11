from . import auth

from flask import jsonify

@auth.route('/signout', methods=['POST'])
def signout():
    response = jsonify()
    response.set_cookie('refresh_token_cookie', value = '', httponly = True, expires=0)
    return response