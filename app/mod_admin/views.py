from collections import OrderedDict

from flask import Blueprint
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import admin_permission
from forms import UserRoleForm
from app.models import *
from app.competence import s

admin = Blueprint('admin', __name__, template_folder='templates')

@admin.route('/')
@admin_permission.require(http_exception=403)
def index():
    return render_template("admin.html")


@admin.route('/userroles', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def userroles():
    form = UserRoleForm()

    if request.method == 'POST':

        u = UserRolesRef(role=request.form["role"])
        s.add(u)
        s.commit()

    user_roles = s.query(UserRolesRef).all()

    return render_template("userroles.html", form=form, data=user_roles)

@admin.route('/userroles/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def userroles_edit(id=None):
    form = UserRoleForm()
    user_role = s.query(UserRolesRef).filter_by(id=id).first()
    form.role.data = user_role.role

    if request.method == 'POST':
        s.query(UserRolesRef).filter_by(id=id).update({'role': request.form["role"]})
        s.commit()
        return redirect(url_for('admin.userroles'))

    return render_template("userroles_edit.html", form=form, id=id)

@admin.route('/userroles/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deleterole(id=None):

    s.query(UserRolesRef).filter_by(id=id).delete()

    s.commit()

    return redirect(url_for('admin.userroles'))


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