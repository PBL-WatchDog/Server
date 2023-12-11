from flask import Blueprint, jsonify
from .mngr import mngr
from .auth import auth
from .user import user

api = Blueprint('api', __name__)

api.register_blueprint(mngr, url_prefix='/mngr')
api.register_blueprint(auth, url_prefix='/auth')
api.register_blueprint(user, url_prefix='/user')

@api.app_errorhandler(404)
def api_error_handling_404(error):
    return jsonify({"msg":"404 not found error"}), 404

@api.app_errorhandler(Exception)
def api_error_handling_500(error):
    # return jsonify({"msg":str(error)}), 500
    return jsonify({"msg":"internal server error"}), 500