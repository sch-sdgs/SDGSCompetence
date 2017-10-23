from flask import Flask, render_template, redirect, request, url_for, session, current_app, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from activedirectory import UserAuthentication
from forms import Login
from flask_principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, Permission, RoleNeed, UserNeed,identity_loaded
from sqlalchemy.sql.expression import func, and_, case

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
        """
        user class to login the user and store useful information. Access attributes of this class with
        "current_user"

        :param id: user id
        :param password: password
        """
        self.id = id
        self.database_id = self.get_database_id()
        self.password = password
        self.roles = self.get_user_roles()
        self.full_name = self.get_full_name()

    def get_database_id(self):
        """
        gets the id of the row in the database for the user.
        :return: database id
        """
        query= s.query(Users).filter_by(login=self.id).first()
        if query:
            database_id = query.id
        else:
            database_id = None
        return database_id

    def get_user_roles(self):
        """
        gets the roles assigned to this user from the database i.e ADMIN, USER etc
        :return: list of user roles
        """
        result = []
        roles = s.query(UserRolesRef).join(UserRoleRelationship).join(Users).filter(Users.login == self.id).all()
        for role in roles:
            result.append(role.role)
        return result

    def get_full_name(self):
        """
        gets user full name given username, helpful for putting name on welcome pages etc
        :return: full name
        """
        user = s.query(Users).filter_by(login=self.id).first()
        full_name = user.first_name + " " + user.last_name
        return full_name


    def is_authenticated(self, id, password):
        """
        checks if user can authenticate with given user id and password. A user can authenticate if two conditions are met
         1. user is in the stardb database
         2. user credentils authenticate with active directory

        :param id: username
        :param password: password
        :return: True/False user is authenticated
        """
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
    """
    handles 404 errors
    :param e:
    :return: template 404.html
    """
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """
    handles 500 errors
    :param e:
    :return: template 500.html
    """
    return render_template('500.html'), 500

@app.errorhandler(403)
def page_not_found(e):
    """
    handles 403 errors (no permission i.e. if not admin)
    :param e:
    :return: template login.html
    """
    session['redirected_from'] = request.url
    return redirect(url_for('login'))

def get_competence_from_subsections(subsection_ids):

    subsections = s.query(Competence).join(Subsection).filter(Subsection.id.in_(subsection_ids)).all()

    return subsections

#####################
# context processor #
#####################
@app.context_processor
def utility_processor():
    def get_percent(c_id, u_id):
        """
        gets the percentage complete of any competence
        :param c_id: competence id
        :param u_id: user id
        :return: percentage complete
        """
        counts = s.query(Assessments).join(Subsection)\
            .filter(and_(Assessments.user_id == u_id, Subsection.c_id == c_id))\
            .values((func.sum(case([(Assessments.date_completed == None, 0)], else_=1)) / func.count(Assessments.id)*100).label('percentage'))
        for c in counts:
            return c.percentage
    return dict(get_percent=get_percent)

#########
# views #
#########
@app.route('/autocomplete_user',methods=['GET'])
def autocomplete():
    """
    autocompletes a user once their name is being types
    :return: jsonified list of users for ajax to use
    """
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
    """
    method to login user
    :return: either login.html or if successful the page the user was trying to access
    """
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
    """
    method to logout the user
    :return: the login page
    """
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
    """
    displays the users dashboard
    :return: template index.html
    """
    with admin_permission.require():
        linereports = s.query(Users).filter_by(line_managerid=int(current_user.database_id)).filter_by(active=True).all()
        linereports_inactive = s.query(Users).filter_by(line_managerid=int(current_user.database_id)).filter_by(
            active=False).count()
    print linereports
    counts = {}
    active_count=0
    assigned_count=0
    for i in linereports:
        counts[i.id] = {}
        #TODO get competence because assessments is all subsections

        counts[i.id]["assigned"] = len(s.query(Competence).join(Subsection).join(Assessments).filter(Assessments.user_id==i.id).filter(Assessments.status==2).all())
        assigned_count += counts[i.id]["assigned"]
        counts[i.id]["active"] = len(s.query(Competence).join(Subsection).join(Assessments).filter(Assessments.user_id==i.id).filter(Assessments.status==1).all())
        active_count += counts[i.id]["active"]
        counts[i.id]["complete"] = len(s.query(Competence).join(Subsection).join(Assessments).filter(Assessments.user_id==i.id).filter(Assessments.status==3).all())
        counts[i.id]["failed"] = len(s.query(Competence).join(Subsection).join(Assessments).filter(Assessments.user_id==i.id).filter(Assessments.status==5).all())
        counts[i.id]["obsolete"] = len(s.query(Competence).join(Subsection).join(Assessments).filter(Assessments.user_id==i.id).filter(Assessments.status==6).all())
        counts[i.id]["abandoned"] = len(s.query(Competence).join(Subsection).join(Assessments).filter(Assessments.user_id==i.id).filter(Assessments.status==4).all())


    competences_incomlete = s.query(CompetenceDetails).join(Competence).filter(CompetenceDetails.creator_id==current_user.database_id).filter(Competence.current_version==0).all()
    competences_complete = s.query(CompetenceDetails).join(Competence).filter(
        CompetenceDetails.creator_id == current_user.database_id).filter(Competence.current_version == 1).all()

    assigned = s.query(Assessments).join(Subsection).join(Competence).join(CompetenceDetails).group_by(CompetenceDetails.id).filter(Assessments.user_id==current_user.database_id).filter(Assessments.status==2).all()
    active = s.query(Assessments).join(Subsection).join(Competence).join(CompetenceDetails).group_by(
        CompetenceDetails.id).filter(Assessments.user_id == current_user.database_id).filter(
        Assessments.status == 1).all()


    return render_template("index.html",assigned_count=assigned_count,active_count=active_count,linereports=linereports,linereports_inactive=linereports_inactive,competences_incomplete=competences_incomlete, competences_complete=competences_complete,counts=counts,assigned=assigned,active=active)

