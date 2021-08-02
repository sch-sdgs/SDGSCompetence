from app.competence import s, send_mail_unknown
from app.models import *
from app.views import admin_permission
from app.activedirectory import UserAuthentication
from flask import flash, render_template, request, url_for, redirect, Blueprint
from flask_login import login_required, current_user

hos = Blueprint('hos', __name__, template_folder='templates')

@hos.route('/service_overview')
#TODO add HOS permission require
#@hos_permission.require(http_exception=403)
def index():
    """
    shows the head of service homepage
    return: template service_overview.html
    """
    return render_template('service_overview.html')