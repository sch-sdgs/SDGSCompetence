from flask import flash,Flask, render_template, redirect, request, url_for, session, current_app, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from activedirectory import UserAuthentication
from forms import *
from flask_principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, Permission, RoleNeed, UserNeed, identity_loaded

from app.mod_training.views import get_competence_summary_by_user
from dateutil.relativedelta import relativedelta
from sqlalchemy.sql.expression import func, and_, or_, case, exists, update,distinct
import os
from trello import TrelloApi
from app.competence import app, s, db
from app.models import *
from app.competence import config
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

import itertools

import json
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

principals = Principal(app)

# permission levels

user_permission = Permission(RoleNeed('USER'))
linemanager_permission = Permission(RoleNeed('LINEMANAGER'))
admin_permission = Permission(RoleNeed('ADMIN'))
privilege_perminssion = Permission(RoleNeed('PRIVILEGE'))


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    form = RegistrationForm()
    if request.method == 'GET':
        db.create_all()
        db.session.commit()

        if s.query(Users).count()==0:

            #create required roles
            roles = ["USER","LINEMANAGER","ADMIN","PRIVILEDGE"]
            for role in roles:
                if s.query(UserRolesRef).filter(UserRolesRef.role==role).count() == 0:
                    r = UserRolesRef(role=role)
                    s.add(r)
                s.commit

            #create statuses
            statuses = ["Abandoned","Active","Assigned","Complete","Failed","Four Year Due","Obsolete","Sign-Off"]
            for status in statuses:
                if s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == status).count() == 0:
                    st = AssessmentStatusRef(status=status)
                    s.add(st)
            s.commit()

            months = [6,12,24,48]
            for month in months:
                if s.query(ValidityRef).filter(ValidityRef.months == month).count() == 0:
                    vr = ValidityRef(months=month)
                    s.add(vr)
            s.commit()

            categories = ["Software"]
            for category in categories:
                if s.query(CompetenceCategory).filter(CompetenceCategory.category == category).count() == 0:
                    cc = CompetenceCategory(category=category)
                    s.add(cc)
            s.commit()

            evidences = ["Case", "Completed competence panel", "Discussion", "Observation", "Upload"]
            for evidence in evidences:
                if s.query(EvidenceTypeRef).filter(EvidenceTypeRef.type == evidence).count() == 0:
                    st = EvidenceTypeRef(type=evidence)
                    s.add(st)
            s.commit()

            #create using competenceDB competence?


            return render_template("setup.html",form=form)
        else:
            return render_template("login.html",form=Login())
    if request.method == 'POST':
        if s.query(Users).count() == 0:
            user = Users(login=form.username.data, email=form.email.data, first_name=form.first_name.data,
                         password=form.password.data, last_name=form.last_name.data, serviceid=None, active=True)


            s.add(user)
            role_id = s.query(UserRolesRef).filter(UserRolesRef.role=="ADMIN").first().id
            role = UserRoleRelationship(user_id=user.id,userrole_id=role_id)
            s.add(role)

            c = Config(key="ORGANISATION",value=form.organisation.data)
            s.add(c)
            s.commit()
            return render_template("login.html", form=Login())

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

from app.forms import RegistrationForm

# ...

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if request.method == 'POST':
        print form.username.data
        if form.service_id.data:
            service_id = form.service_id.data.id
        else:
            service_id = None
        user = Users(login=form.username.data, email=form.email.data, first_name=form.first_name.data, password=form.password.data, last_name=form.last_name.data , serviceid=service_id, active=True)
        print user
        s.add(user)

        s.commit()
        flash('Congratulations, you are now a registered user!','success')
        return redirect(url_for('login'))
    if "invite_id" in request.args:
        invite_id = request.args["invite_id"]
        invite = s.query(Invites).filter(Invites.invite_id == invite_id).first()
        if invite:
            form.username.data = invite.email
            form.first_name.data = invite.first_name
            form.last_name.data = invite.last_name
            form.email.data = invite.email
            return render_template('register.html', title='Register', form=form)
        else:
            return "You do not have an invite"
    else:
        return "Forbidden"

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
        query = s.query(Users).filter_by(login=self.id).first()
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
        if user is not None:
            full_name = user.first_name + " " + user.last_name
            return full_name
        else:
            return False

    def check_password(self, password):
        return check_password_hash(password,self.password)

    def is_authenticated(self, id, password):
        """
        checks if user can authenticate with given user id and password. A user can authenticate if two conditions are met
         1. user is in the stardb database
         2. user credentils authenticate with active directory

        :param id: username
        :param password: password
        :return: True/False user is authenticated
        """

        #check user is registered
        user = s.query(Users).filter_by(login=id).all()
        if len(list(user)) == 0:
            return False
        #check if using active directory
        if config.get("ACTIVE_DIRECTORY"):
            check = UserAuthentication().authenticate(id, password)
        else:
            check = self.check_password(user[0].password)

        print "HERE"
        print check
        if check:
            data = {"last_login": datetime.date.today()}
            s.query(Users).filter(Users.login == id).update(data)
            s.commit()

            roles = s.query(UserRolesRef).join(UserRoleRelationship).join(Users).filter(Users.login == id).all()
            for role in roles:
                self.roles.append(role.role)

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
            # identity.provides.add(RoleNeed(role.name))
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
    def get_percent(c_id, u_id,version):
        """
        gets the percentage complete of any competence
        :param c_id: competence id
        :param u_id: user id
        :return: percentage complete
        """
        counts = s.query(Assessments)\
            .join(Subsection) \
            .join(AssessmentStatusRef) \
            .filter(Assessments.version==version) \
            .filter(AssessmentStatusRef.status != "Obsolete")\
            .filter(and_(Assessments.user_id == u_id, Subsection.c_id == c_id)) \
            .values((func.sum(case([(Assessments.date_completed == None, 0)], else_=1)) / func.count(
            Assessments.id) * 100).label('percentage'))
        for c in counts:
            return c.percentage

    return dict(get_percent=get_percent)


@app.context_processor
def utility_processor():
    def friendly_date(date):
      if type(date) == str:
          result=date
      else:
          result = date.strftime("%d-%m-%Y")
      return result

    return dict(friendly_date=friendly_date)

@app.context_processor
def utility_processor():
    def count_active(c_id, u_id):
        """
        gets the percentage complete of any competence
        :param c_id: competence id
        :param u_id: user id
        :return: percentage complete
        """
        counts = s.query(Assessments)\
            .join(Subsection)\
            .join(AssessmentStatusRef)\
            .filter(and_(Assessments.user_id == u_id, Subsection.c_id == c_id)) \
            .values((func.sum(
            case([(or_(AssessmentStatusRef.status.in_(["Active", "Complete","Failed"])), 1)],
                 else_=0)) / func.count(Assessments.id) * 100).label('percentage'))
        for c in counts:
            return c.percentage

    return dict(count_active=count_active)

def check_margin(date,margin_days):
    today = datetime.date.today()
    if margin_days == 0:
        margin = datetime.timedelta()
    else:
        margin = datetime.timedelta(days=margin_days)
    if date is not None:
        if date < today:
            result = True
        else:
            result = today - margin <= date <= today + margin
    else:
        result = False
    print result
    return result

@app.context_processor
def utility_processor():
    def check_expiry(expiry_date):
        if check_margin(expiry_date,0):
            html = '<span class="label label-danger">Expired</span>'
        elif check_margin(expiry_date,5):
            html = '<span class="label label-danger">Expiring Within 5 Days</span>'
        elif check_margin(expiry_date,30):
            html = '<span class="label label-warning">Expiring Within 30 Days</span>'
        elif check_margin(expiry_date, 90):
            html = '<span class="label label-info">Expiring Within Days</span>'
        else:
            html = '<span class="label label-success">OK</span>'

        return html

    return dict(check_expiry=check_expiry)

@app.context_processor
def utility_processor():
    def get_reassessment_status(reassessment):


        if reassessment.is_correct == None:
            html = '<span class ="label label-warning">Awaiting Sign-Off</span>'
        elif reassessment.is_correct == 1:
            html = '<span class ="label label-success">Approved</span>'
        elif reassessment.is_correct == 0:
            html = '<span class ="label label-danger">Failed</span>'


        return html

    return dict(get_reassessment_status=get_reassessment_status)

def percent_due_date(assigned_date,due_date):
    days_passed_since_assignment = abs((assigned_date - datetime.date.today()).days)

    total_days = abs((due_date - assigned_date).days)

    if total_days == 0:
        percent = 100
    else:
        percent = (days_passed_since_assignment / float(total_days)) * float(100)

    return percent

@app.context_processor
def utility_processor():
    def check_due_date(assigned_date,due_date):

        percent = percent_due_date(assigned_date,due_date)

        if percent > 90:
            html = '<span class="label label-danger">'+due_date.strftime('%d-%m-%Y')+'</span>'
        elif percent > 70:
            html = '<span class="label label-warning">'+due_date.strftime('%d-%m-%Y')+'</span>'
        elif percent >= 0:
            html = '<span class="label label-success">'+due_date.strftime('%d-%m-%Y')+'</span>'

        return html

        #return {"total_days":total_days,"days_passed":days_passed_since_assignment}


        # if check_margin(expiry_date,0):
        #     html = '<span class="label label-danger">Expired</span>'
        # elif check_margin(expiry_date,5):
        #     html = '<span class="label label-danger">Expiring Within 5 Days</span>'
        # elif check_margin(expiry_date,30):
        #     html = '<span class="label label-warning">Expiring Within 30 Days</span>'
        # elif check_margin(expiry_date, 90):
        #     html = '<span class="label label-info">Expiring Within Days</span>'
        # else:
        #     html = '<span class="label label-success">OK</span>'

        #return html

    return dict(check_due_date=check_due_date)


def assess_status_method(status):
    if status == "Active":
        html = '<span class="label label-warning">Active</span>'
    elif status == "Complete":
        html = '<span class="label label-success">Complete</span>'
    elif status == "Assigned":
        html = '<span class="label label-default">Assigned</span>'
    elif status == "Four Year Due":
        html = '<span class="label label-danger">Four Year Due</span>'

    return html


@app.context_processor
def utility_processor():
    def assess_status(status):
        html = assess_status_method(status)

        return html

    return dict(assess_status=assess_status)

@app.context_processor
def utility_processor():
    def get_status(status_id):
        status = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.id==status_id).first().status
        html = assess_status_method(status)

        return html

    return dict(get_status=get_status)


@app.context_processor
def utility_processor():
    def notifications():
        expired = s.query(Assessments).filter(Assessments.user_id == current_user.database_id)
        alerts = {}
        count=0
        for i in expired:
            if i.date_expiry is not None:
                if datetime.date.today() > i.date_expiry:
                    if "Assessments Expired" not in alerts:
                        alerts["Assessments Expired"] = 1
                        count+=1
                    else:
                        alerts["Assessments Expired"] += 1
                        count+=1
                elif datetime.date.today() + relativedelta(months=+6) > i.date_expiry:
                    if "Assessments Expiring" not in alerts:
                        alerts["Assessments Expiring"] = 1
                        count += 1
                    else:
                        alerts["Assessments Expiring"] += 1
                        count += 1
        signoff = s.query(Evidence).filter(Evidence.signoff_id == current_user.database_id).filter(Evidence.is_correct == None).count()
        if signoff > 0:
            count+=signoff
            alerts["Evidence Approval"] = signoff
        approval = s.query(CompetenceDetails).filter(and_(CompetenceDetails.approve_id == current_user.database_id,CompetenceDetails.approved != None,CompetenceDetails.approved != 1)).count()
        if approval > 0:
            count += approval
            alerts["Competence Approval"] = approval
        reassessments = s.query(Reassessments).filter(Reassessments.signoff_id == current_user.database_id).filter(Reassessments.is_correct==None).count()
        if reassessments > 0:
            count += reassessments
            alerts["Reassessment Approval"] = reassessments

        return [count,alerts]
    return dict(notifications=notifications)

@app.context_processor
def utility_processor():
    def get_approval_status(approved):
        if approved == None:
            return '<small class="label bg-gray">Not Submitted</small>'
        elif approved == True:
            return '<small class="label bg-green">Approved</small>'
        elif approved == False:
            return '<small class="label bg-orange">Awaiting Approval</small>'
    return dict(get_approval_status=get_approval_status)




#########
# views #
#########

@app.route('/autocomplete_linemanager', methods=['GET'])
def autocomplete_linemanager():
    """
    autocompletes a user once their name is being types
    :return: jsonified list of users for ajax to use
    """
    search = request.args.get('linemanager')

    linemanagers = s.query(Users).join(UserRoleRelationship).filter(Users.active==1).filter(UserRoleRelationship.userrole_id==2).all()
    # users = s.query(Users.first_name, Users.last_name).filter(Users.active==1).filter()all()
    manager_list = []
    for i in linemanagers:
        name = i.first_name + " " + i.last_name
        manager_list.append(name)

    print manager_list

    return jsonify(json_list=manager_list)

@app.route('/autocomplete_user', methods=['GET'])
def autocomplete():
    """
    autocompletes a user once their name is being types
    :return: jsonified list of users for ajax to use
    """
    search = request.args.get('linemanager')

    users = s.query(Users.first_name, Users.last_name).filter(Users.active==1).all()
    user_list = []
    for i in users:
        name = i[0] + " " + i[1]
        user_list.append(name)

    return jsonify(json_list=user_list)


@app.route('/autocomplete_subsection', methods=['GET'])
def autocomplete_subsection():
    """
    autocompletes a user once their name is being types
    :return: jsonified list of users for ajax to use
    """
    search = request.args.get('name')

    phrases = s.query(SubsectionAutocomplete.phrase).all()
    phrase_list = []
    for i in phrases:
        print i
        phrase_list.append(i[0])

    return jsonify(json_list=phrase_list)

@app.route('/autocomplete_competent_user/<int:ss_id>', methods=['GET'])
def autocomplete_competent_user(ss_id):
    # todo: add competence author to this list
    users = s.query(Users). \
        join(Assessments, Assessments.user_id == Users.id). \
        join(AssessmentStatusRef). \
        filter(AssessmentStatusRef.status == "Complete",
               Assessments.date_expiry > datetime.date.today()). \
        group_by(Users.id).having(func.count(Assessments.ss_id == ss_id) == 1). \
        values(Users.id, (Users.first_name + ' ' + Users.last_name).label('name'))
    user_list = []
    for i in users:
        user = {}
        user["id"] = i.id
        user["name"] = i.name
        user_list.append(user)

    return jsonify(users=user_list)


@app.route('/check_valid_user', methods=['GET', 'POST'])
def check_valid_user():
    if " " in request.args["name"]:
        first_name,last_name=request.args["name"].split(" ")
        result = s.query(Users).filter(and_(Users.first_name == first_name,Users.last_name == last_name)).count()

        if result == 0:
            return jsonify({"response":False})
        if result == 1:
            return jsonify({"response":True})
    else:
        return jsonify({"response": False})


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    method to login user
    :return: either login.html or if successful the page the user was trying to access
    """
    form = Login(next=request.args.get('next'))
    if request.method == 'GET':
        return render_template("login.html", org=config.get("ORGANISATION"), form=form)
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
            flash("Wrong username or password!","danger")
            return render_template("login.html", org=config.get("ORGANISATION"), form=form)


@app.route('/login_as', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def login_as():
    """
    method to login user
    :return: either login.html or if successful the page the user was trying to access
    """
    form = Login(next=request.args.get('next'))
    if request.method == 'GET':
        return render_template("login_as.html", form=form)
    elif request.method == 'POST':
        user = User(form.data["username"])
        result = True
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

@app.route('/index')
@login_required
def home():
    return redirect('/')

@app.route('/')
@login_required
def index(message=None):
    """
    displays the users dashboard
    :return: template index.html
    """

    linereports = s.query(Users).filter_by(line_managerid=int(current_user.database_id)).filter_by(active=True).all()
    linereports_inactive = s.query(Users).filter_by(line_managerid=int(current_user.database_id)).filter_by(
        active=False).count()
    counts = {}
    active_count = 0
    assigned_count = 0
    complete_count = 0
    abandoned_count = 0
    signoff_count = 0
    failed_count = 0
    expiring_count = 0
    expired_count = 0

    for i in linereports:
        counts[i.id] = {}
        # TODO get competence because assessments is all subsections

        #TODO using IDs instead of name here

        counts[i.id]["assigned"] = len(
            s.query(Assessments).join(AssessmentStatusRef).filter(Assessments.user_id == i.id).filter(
                AssessmentStatusRef.status == "Assigned").all())
        assigned_count += counts[i.id]["assigned"]
        counts[i.id]["active"] = len(
            s.query(Assessments).join(AssessmentStatusRef).filter(Assessments.user_id == i.id).filter(
                AssessmentStatusRef.status == "Active").all())
        active_count += counts[i.id]["active"]
        counts[i.id]["sign-off"] = len(
            s.query(Assessments).join(AssessmentStatusRef).filter(Assessments.user_id == i.id).filter(
                AssessmentStatusRef.status == "Sign-Off").all())
        signoff_count += counts[i.id]["sign-off"]
        counts[i.id]["complete"] = len(
            s.query(Assessments).join(AssessmentStatusRef).filter(Assessments.user_id == i.id).filter(
                AssessmentStatusRef.status == "Complete").all())
        complete_count += counts[i.id]["complete"]
        counts[i.id]["failed"] = len(
            s.query(Assessments).join(AssessmentStatusRef).filter(Assessments.user_id == i.id).filter(
                AssessmentStatusRef.status == "Failed").all())
        failed_count += counts[i.id]["failed"]
        counts[i.id]["obsolete"] = len(
            s.query(Assessments).join(AssessmentStatusRef).filter(Assessments.user_id == i.id).filter(
                AssessmentStatusRef.status == "Obsolete").all())
        counts[i.id]["abandoned"] = len(
            s.query(Assessments).join(AssessmentStatusRef).filter(Assessments.user_id == i.id).filter(
                AssessmentStatusRef.status == "Abandoned").all())
        abandoned_count += counts[i.id]["abandoned"]

    expired = s.query(Assessments).filter(Assessments.user_id == current_user.database_id)
    alerts = {}
    alerts["Assessments"] = {}
    for i in linereports:
        ass = s.query(Assessments).filter(Assessments.user_id == i.id).all()
        for j in ass:
            if j.date_expiry is not None:
                if datetime.date.today() > j.date_expiry:
                    if "expired" not in counts[i.id]:
                        counts[i.id]["expired"] = 0
                        counts[i.id]["expired"] += 1
                    else:
                        counts[i.id]["expired"] += 1

                    expired_count += 1

                elif datetime.date.today() + relativedelta(months=+6) > j.date_expiry:
                    if "expiring" not in counts[i.id]:
                        counts[i.id]["expiring"] = 0
                        counts[i.id]["expiring"] += 1

                    else:
                        counts[i.id]["expiring"] += 1
                    expiring_count += 1


    competences_incomplete = s.query(CompetenceDetails).join(Competence).filter(
        CompetenceDetails.creator_id == current_user.database_id).filter(Competence.current_version != CompetenceDetails.intro).filter(CompetenceDetails.date_of_approval == None).all()



    competences_complete = s.query(CompetenceDetails).join(Competence).filter(
        CompetenceDetails.creator_id == current_user.database_id).filter(Competence.current_version == CompetenceDetails.intro).all()




    # assigned = s.query(Assessments).filter(Assessments.user_id == current_user.database_id).filter(
    #     or_(Assessments.status == 2, Assessments.status == 1, Assessments.status == 7)).filter(Competence.current_version==Assessments.version).all()
    #

    assigned = s.query(Assessments)\
        .join(Subsection)\
        .join(Competence)\
        .join(CompetenceDetails)\
        .join(AssessmentStatusRef)\
        .filter(Assessments.user_id == current_user.database_id)\
        .group_by(Competence.id)\
        .filter(or_(AssessmentStatusRef.status == "Assigned", AssessmentStatusRef.status == "Active", AssessmentStatusRef.status == "Sign-Off"))\
        .all()
    print "ME"
    print assigned
    # assigned = s.query(Assessments).join(Subsection).join()

    all_assigned=[]
    for j in assigned:
        all_assigned.append(get_competence_summary_by_user(c_id=j.ss_id_rel.c_id,u_id=current_user.database_id,version=j.version))

    active = s.query(Assessments)\
        .join(Subsection)\
        .join(Competence)\
        .join(CompetenceDetails)\
        .join(AssessmentStatusRef)\
        .group_by(CompetenceDetails.id)\
        .filter(Assessments.user_id == current_user.database_id)\
        .filter(CompetenceDetails.intro==Competence.current_version)\
        .filter(AssessmentStatusRef.status == "Active").all()

    complete = s.query(Assessments) \
        .join(Subsection)\
        .join(Competence)\
        .join(CompetenceDetails)\
        .join(AssessmentStatusRef)\
        .filter(Assessments.user_id == current_user.database_id) \
        .group_by(Assessments.version) \
        .filter(AssessmentStatusRef.status.in_(["Complete","Four Year Due"])) \
        .all()


    print complete
    all_complete = []
    for i in complete:
        print "COMPLETE"
        print i
        result = get_competence_summary_by_user(c_id=i.ss_id_rel.c_id, u_id=current_user.database_id, version=i.version)
        if result.completed != None:
            all_complete.append(result)
    print all_complete
    obsolete = s.query(Assessments) \
        .join(Subsection) \
        .join(Competence) \
        .join(CompetenceDetails) \
        .join(AssessmentStatusRef) \
        .filter(Assessments.user_id == current_user.database_id) \
        .filter(and_(CompetenceDetails.intro <= Assessments.version,or_(CompetenceDetails.last >= Assessments.version,CompetenceDetails.last==None)))\
        .group_by(Competence.id) \
        .filter(AssessmentStatusRef.status.in_(["Obsolete"])) \
        .all()

    # print "HELLO"
    # print obsolete
    # all_obsolete = []
    # for i in obsolete:
    #     print "OBSOLETE"
    #     print i
    #     result = get_competence_summary_by_user(c_id=i.ss_id_rel.c_id, u_id=current_user.database_id, version=i.version)
    #     if result.completed != None:
    #         all_obsolete.append(result)


    signoff = s.query(Evidence).filter(Evidence.signoff_id == current_user.database_id).filter(Evidence.is_correct == None).all()
    signoff_competence = s.query(CompetenceDetails).filter(and_(CompetenceDetails.approve_id == current_user.database_id,CompetenceDetails.approved != None,CompetenceDetails.approved != 1)).all()
    print "SIGN_OFF"
    print signoff_competence
    signoff_reassessment = s.query(Reassessments).join(AssessReassessRel).join(Assessments).filter(Reassessments.signoff_id==current_user.database_id).filter(Reassessments.is_correct == None).all()

    # signoff_reassessments = {key: [i for i in value] for key, value in
    #           itertools.groupby(signoff_reassessment, lambda item: item.assess_rel.user_id_rel )}




    accept_form = RateEvidence()
    return render_template("index.html", message=message, expiring_count=expiring_count, expired_count=expired_count, complete=all_complete, obsolete=obsolete, accept_form=accept_form, signoff=signoff, assigned_count=assigned_count,
                           active_count=active_count, signoff_count=signoff_count, failed_count=failed_count, complete_count=complete_count, linereports=linereports,
                           linereports_inactive=linereports_inactive, competences_incomplete=competences_incomplete,
                           competences_complete=competences_complete, abandoned_count=abandoned_count, counts=counts, assigned=all_assigned, active=active,signoff_competence=signoff_competence,signoff_reassessment=signoff_reassessment)


@app.route('/notifications')
@login_required
def notifications():
    expired = s.query(Assessments).filter(Assessments.user_id == current_user.database_id)
    alerts = {}
    alerts["Assessments"]={}
    count = 0
    for i in expired:
        if i.date_expiry is not None:
            if datetime.date.today() > i.date_expiry:
                if "Assessments Expired" not in alerts["Assessments"]:
                    alerts["Assessments"]["Assessments Expired"] = []
                    alerts["Assessments"]["Assessments Expired"].append(i)
                    count += 1
                else:
                    alerts["Assessments"]["Assessments Expired"].append(i)
                    count += 1
            elif datetime.date.today() + relativedelta(months=+6) > i.date_expiry:
                if "Assessments Expiring" not in alerts["Assessments"]:
                    alerts["Assessments"]["Assessments Expiring"] = []
                    alerts["Assessments"]["Assessments Expiring"].append(i)
                    count += 1
                else:
                    alerts["Assessments"]["Assessments Expiring"]
                    count += 1

    signoff = s.query(Evidence).filter(Evidence.signoff_id == current_user.database_id).filter(
        Evidence.is_correct == None).count()
    if signoff > 0:
        count += signoff
        signoff_query = s.query(Evidence).filter(Evidence.signoff_id == current_user.database_id).filter(
            Evidence.is_correct == None).all()
        alerts["Evidence Approval"] = signoff_query
    approval = s.query(CompetenceDetails).filter(
        and_(CompetenceDetails.approve_id == current_user.database_id, CompetenceDetails.approved != None,
             CompetenceDetails.approved != 1)).count()
    if approval > 0:
        count += approval
        approval_query = s.query(CompetenceDetails).filter(
            and_(CompetenceDetails.approve_id == current_user.database_id, CompetenceDetails.approved != None,
                 CompetenceDetails.approved != 1)).all()
        alerts["Competence Approval"] = approval_query

    reassessments = s.query(Reassessments).filter(Reassessments.signoff_id == current_user.database_id).filter(
        Reassessments.is_correct == None).count()
    if reassessments > 0:
        count += reassessments
        reassessments_query = s.query(Reassessments).filter(Reassessments.signoff_id == current_user.database_id).filter(
            Reassessments.is_correct == None).all()
        alerts["Reassessment Approval"] = reassessments_query



    return render_template("notifications.html",alerts=alerts)

@app.route('/bug_reports', methods=['POST','GET'])
@login_required
def bug_reports():

    trello = TrelloApi(config.get("TRELLO_APP_KEY"),token='1c7e2c946ba584da3e125834ebc88f41f38a3f6286ee99e9a43682902ca82ccb')
    token = trello.get_token_url('My App', expires='30days', write_access=True)

    for i in trello.boards.get_list('59de4d6e5c1d9536f21019d9'):
        if i["name"] == "Bug Reports":
            list_id = i["id"]


    if request.method == 'POST':
        trello.cards.new(request.form["bug"] + "- " + current_user.full_name,list_id)

    current_bugs = trello.lists.get_card(list_id=list_id)

    return render_template("bug_reports.html",current_bugs=current_bugs)
