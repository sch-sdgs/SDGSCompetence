from flask import Flask, render_template, redirect, request, url_for, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from activedirectory import UserAuthentication
from forms import Login
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, Permission, RoleNeed, UserNeed,identity_loaded
from competence import app

import os

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"

principals = Principal(app)

#permission levels

user_permission = Permission(RoleNeed('user'))
linemanager_permission = Permission(RoleNeed('linemanager'))
admin_permission = Permission(RoleNeed('admin'))
superadmin_permission = Permission(RoleNeed('superadmin'))


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

class User(UserMixin):
    def __init__(self, id, password=None, roles=None):
        self.id = id
        self.password = password
        self.roles = ['admin','linemanager']

    def is_authenticated(self, id, password):
        # validuser = get_user_by_username(s, id)
        #
        # if len(list(validuser)) == 0:
        #     return False
        # else:
        check_activdir = UserAuthentication().authenticate(id, password)

        if check_activdir != "False":
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
    return render_template("index.html")

