from flask import Blueprint
from datetime import timedelta
import re

ACCESS_EXPIRED = timedelta(minutes=15)
REFRESH_EXPIRED = timedelta(days=7)

NAME_REGEX = re.compile("^[가-힣]{2,4}$", re.M)
PHONE_REGEX = re.compile("^[0-9]{11}$", re.M)

auth = Blueprint('auth', __name__)

from . import signup, signin, signout, refresh