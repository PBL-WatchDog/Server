from flask import Flask
from flask_jwt_extended import JWTManager

from main.config.config import JWT_SECRET_KEY

from main.api import api

from flask_cors import CORS


app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r'*': {'origins': ["*","http://211.57.200.6:3333"]}})
app.config['SECRET_KEY'] = JWT_SECRET_KEY
jwt = JWTManager(app)

app.register_blueprint(api, url_prefix='/api/v1')