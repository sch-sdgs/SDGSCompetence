from collections import OrderedDict

from flask import Blueprint
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import admin_permission

admin = Blueprint('admin', __name__, template_folder='templates')

@admin.route('/')
@admin_permission.require(http_exception=403)
def index():
    return render_template("admin.html")


@admin.route('/user', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def user_admin():
    pass



@admin.route('/logs', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def view_logs():
    pass


@admin.route('/application', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def application_admin():
    pass