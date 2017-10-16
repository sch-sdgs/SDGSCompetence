from collections import OrderedDict
from sqlalchemy.orm import load_only
from flask import Blueprint
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import admin_permission
from forms import UserRoleForm, UserForm, UserEditForm
from app.models import *
from app.competence import s
import datetime
import time

admin = Blueprint('admin', __name__, template_folder='templates')

@admin.route('/')
@admin_permission.require(http_exception=403)
def index():
    return render_template("admin.html")

def convertTimestampToSQLDateTime(value):
    return time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(value))



@admin.route('/users/view', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def users_view():

    users = s.query(Users).all()
    data = []
    for user in users:

        jobs = s.query(UserJobRelationship).join(JobRoles).filter(UserJobRelationship.user_id==user.id).all()
        roles = s.query(UserRoleRelationship).join(UserRolesRef).filter(UserRoleRelationship.user_id == user.id).all()
        line_manager_result = s.query(Users.first_name,Users.last_name).filter_by(id=user.line_managerid).first()
        print line_manager_result
        user_dict = dict(user)
        user_dict["jobs"] = []
        for i in jobs:
            user_dict["jobs"].append(i.jobroles_id_rel.job)

        user_dict["roles"] = []
        for i in roles:
            user_dict["roles"].append(i.userrole_id_rel.role)
        if line_manager_result is not None:
            user_dict["line_manager_name"] = line_manager_result[0] + " " + line_manager_result[1]
        else:
            user_dict["line_manager_name"] = None

        data.append(user_dict)



    return render_template("users_view.html",data=data)

@admin.route('/users/toggle_active/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def users_toggle_active(id=None):

    user = s.query(Users).filter_by(id=id).first()
    if user.active == True:
        s.query(Users).filter_by(id=id).update({'active': False})
    elif user.active == False:
        s.query(Users).filter_by(id=id).update({'active': True})
    s.commit()
    return redirect(url_for('admin.users_view'))


@admin.route('/users/add', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def users_add():
    form = UserForm()
    if request.method == 'POST':
        now = datetime.datetime.now()


        if request.form["linemanager"] != "":
            firstname,surname = request.form["linemanager"].split(" ")
            line_manager_id = int(s.query(Users).filter_by(first_name=firstname,last_name=surname).first().id)
        else:
            line_manager_id=None


        u = Users(login=request.form["username"],
                  first_name = request.form["firstname"],
                  last_name = request.form["surname"],
                  email=request.form["email"],
                  active=True,
                  line_managerid=line_manager_id)

        s.add(u)
        s.commit()
        print request.form.getlist('userrole')
        for role_id in request.form.getlist('userrole'):
            urr = UserRoleRelationship(userrole_id=int(role_id),user_id=u.id)
            s.add(urr)

        for job_id in request.form.getlist('jobrole'):
            urr = UserJobRelationship(jobrole_id=int(job_id), user_id=u.id)
            s.add(urr)
        s.commit()
        return redirect(url_for('admin.users_view'))




    return render_template("users_add.html",form=form)

@admin.route('/users/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def users_edit(id=None):
    if request.method == 'GET':
        form = UserEditForm()

        user = s.query(Users).filter_by(id=id).first()
        form.username.data = user.login
        form.firstname.data = user.first_name
        form.surname.data = user.last_name
        form.email.data = user.email

        line_manager_result = s.query(Users.first_name, Users.last_name).filter_by(id=user.line_managerid).first()
        if line_manager_result is not None:
            form.linemanager.data = line_manager_result[0] + " " + line_manager_result[1]
        else:
            form.linemanager.data = None


        jobrole_ids = [name for (name,) in s.query(UserJobRelationship.jobrole_id).filter_by(user_id=id).all()]

        form.jobrole.choices = s.query(JobRoles.id,JobRoles.job).all()
        form.jobrole.process_data(jobrole_ids)

        userrole_ids = [name for (name,) in s.query(UserRoleRelationship.userrole_id).filter_by(user_id=id).all()]

        form.userrole.choices = s.query(UserRolesRef.id,UserRolesRef.role).all()
        form.userrole.process_data(userrole_ids)



        return render_template("users_edit.html", id=id, form=form)

    if request.method == 'POST':

        if request.form["linemanager"] != "":
            firstname, surname = request.form["linemanager"].split(" ")
            line_manager_id = int(s.query(Users).filter_by(first_name=firstname, last_name=surname).first().id)
        else:
            line_manager_id = None

        s.query(UserJobRelationship).filter_by(user_id=id).delete()
        s.query(UserRoleRelationship).filter_by(user_id=id).delete()

        for role_id in request.form.getlist('userrole'):
            urr = UserRoleRelationship(userrole_id=int(role_id), user_id=id)
            s.add(urr)

        for job_id in request.form.getlist('jobrole'):
            urr = UserJobRelationship(jobrole_id=int(job_id), user_id=id)
            s.add(urr)
        s.commit()

        data = {
            'login': request.form["username"],
            'first_name': request.form["firstname"],
            'last_name': request.form["surname"],
            'email': request.form["email"],
            'line_managerid': line_manager_id
        }

        s.query(Users).filter_by(id=id).update(data)

        return redirect(url_for('admin.users_view'))

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