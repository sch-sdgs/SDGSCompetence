from flask import Flask, render_template, redirect, request, url_for, session, current_app, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from activedirectory import UserAuthentication
from forms import Login
from flask_principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, Permission, RoleNeed, UserNeed,identity_loaded


import os

from app.competence import app, s, db
from app.models import *

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"

principals = Principal(app)

#permission levels

user_permission = Permission(RoleNeed('USER'))
linemanager_permission = Permission(RoleNeed('LINEMANAGER'))
admin_permission = Permission(RoleNeed('ADMIN'))
privilege_perminssion = Permission(RoleNeed('PRIVILEGE'))

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


class User(UserMixin):
    def __init__(self, id, password=None):
        self.id = id
        self.database_id = self.get_database_id()
        self.password = password
        self.roles = self.get_user_roles()
        print self.roles

    def get_database_id(self):
        query= s.query(Users).filter_by(login=self.id).first()
        if query:
            database_id = query.id
        else:
            database_id = None
        return database_id

    def get_user_roles(self):
        result = []
        roles = s.query(UserRolesRef).join(UserRoleRelationship).join(Users).filter(Users.login == self.id).all()
        for role in roles:
            result.append(role.role)
        return result

    def is_authenticated(self, id, password):

        user = s.query(Users).filter_by(login=id).all()

        if len(list(user)) == 0:
            return False
        else:
            check_activdir = UserAuthentication().authenticate(id, password)

        self.roles = []
        if check_activdir != "False":
            roles = s.query(UserRolesRef).join(UserRoleRelationship).join(Users).filter(Users.login == id).all()
            for role in roles:
                self.roles.append(role.role)
            print self.roles
            return True


        else:
            return False

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    # Assuming the User model has a list of roles, update the
    # identity with the roles that the user provides
    if hasattr(current_user, 'roles'):
        for role in current_user.roles:
            #identity.provides.add(RoleNeed(role.name))
            identity.provides.add(RoleNeed(role))

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.errorhandler(403)
def page_not_found(e):
    session['redirected_from'] = request.url
    return redirect(url_for('login'))

@app.route('/autocomplete_user',methods=['GET'])
def autocomplete():
    search = request.args.get('linemanager')

    users = s.query(Users.first_name,Users.last_name).all()
    user_list = []
    for i in users:
        print i
        name = i[0] + " " + i[1]
        user_list.append(name)

    return jsonify(json_list=user_list)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = Login(next=request.args.get('next'))
    if request.method == 'GET':
        return render_template("login.html", form=form)
    elif request.method == 'POST':
        user = User(form.data["username"], password=form.data["password"])
        result = user.is_authenticated(id=form.data["username"], password=form.data["password"])
        if result:
            login_user(user)
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

            if form.data["next"] != "":
                return redirect(form.data["next"])
            else:
                return redirect(url_for('index'))
        else:
            return render_template("login.html", form=form, modifier="Oh Snap!", message="Wrong username or password")

@app.route('/logout')
@login_required
def logout():
    # Remove the user information from the session
    logout_user()

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())

    return redirect(request.args.get('next') or '/')

@app.route('/')
@login_required
def index():



    with admin_permission.require():
        linereports = s.query(Users).filter_by(line_managerid=int(current_user.database_id)).filter_by(active=True).all()
        linereports_inactive = s.query(Users).filter_by(line_managerid=int(current_user.database_id)).filter_by(
            active=False).count()
    print linereports
    counts = {}
    for i in linereports:
        counts[i.id] = {}
        counts[i.id]["assigned"] = s.query(Assessments).filter_by(user_id=i.id).filter_by(status=2).count()
        counts[i.id]["active"] = s.query(Assessments).filter_by(user_id=i.id).filter_by(status=1).count()
        counts[i.id]["complete"] = s.query(Assessments).filter_by(user_id=i.id).filter_by(status=3).count()
        counts[i.id]["failed"] = s.query(Assessments).filter_by(user_id=i.id).filter_by(status=5).count()
        counts[i.id]["obsolete"] = s.query(Assessments).filter_by(user_id=i.id).filter_by(status=6).count()
        counts[i.id]["abandoned"] = s.query(Assessments).filter_by(user_id=i.id).filter_by(status=4).count()


    print counts

    competences = s.query(Competence).filter_by(creator_id=current_user.database_id).filter_by(current_version=0).all()

    return render_template("index.html",linereports=linereports,linereports_inactive=linereports_inactive,competences=competences,counts=counts)

