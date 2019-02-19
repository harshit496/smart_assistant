import functools
import requests
import alpha_vantage
from flask_googlecharts import BarChart

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from flaskr.db import get_db



bp = Blueprint('homepage', __name__, url_prefix='/home')
my_chart = BarChart("my_chart")




