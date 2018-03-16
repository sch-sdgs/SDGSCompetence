from collections import OrderedDict
from sqlalchemy.orm import load_only
from flask import Blueprint
from flask import render_template, request, url_for, redirect, Blueprint, jsonify, make_response
from flask_login import login_required, current_user
from app.views import admin_permission
from forms import *
from app.models import *
from app.competence import s
import datetime
import time
import io
import os
import csv
from app.activedirectory import UserAuthentication
import codecs
import json

admin = Blueprint('admin', __name__, template_folder='templates')


def convertTimestampToSQLDateTime(value):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(value))


# ajax methods
@admin.route('/get_user_details', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def get_user_details():
    """
    gets user details form active directory based on the username
    :return: json of the results
    """
    username = request.args["username"]
    u = UserAuthentication().get_user_detail_from_username(username)
    return jsonify(u);


@admin.route('/check_line_manager', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def check_line_manager():
    """
    gets user details form active directory based on the username
    :return: json of the results
    """
    linemanager = request.args["linemanager"]
    if " " in linemanager:
        firstname, surname = linemanager.split(" ")
        line_manager_query = s.query(Users).filter_by(first_name=firstname, last_name=surname).first()
        if line_manager_query is not None:
            role_id = int(s.query(UserRolesRef).filter_by(role="LINEMANAGER").first().id)
            check_if_line_manager = s.query(UserRoleRelationship).filter_by(userrole_id=role_id).filter_by(
                user_id=line_manager_query.id).count()
            if check_if_line_manager > 0:
                return jsonify(True)
            else:
                return jsonify(False)
        else:
            return jsonify(False)
    elif linemanager == "":
        return jsonify(False)
    else:
        return jsonify(False)


@admin.route('/')
@admin_permission.require(http_exception=403)
def index():
    """
    shows the admin homepage
    :return: template admin.html
    """
    return render_template("admin.html")


@admin.route('/users/view', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def users_view():
    """
    view all users in the database - roles control how much info you can see
    :return: template users_view.html
    """
    users = s.query(Users).all()
    data = []
    for user in users:

        jobs = s.query(UserJobRelationship).join(JobRoles).filter(UserJobRelationship.user_id == user.id).all()
        roles = s.query(UserRoleRelationship).join(UserRolesRef).filter(UserRoleRelationship.user_id == user.id).all()
        line_manager_result = s.query(Users.first_name, Users.last_name).filter_by(id=user.line_managerid).first()
        user_dict = dict(user)
        user_dict["staff_no"] = user.staff_no
        if user.service_rel:
            user_dict["sectionname"] = user.service_rel.name
        else:
            user_dict["sectionname"] = None
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

    return render_template("users_view.html", data=data)


@admin.route('/users/toggle_active/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def users_toggle_active(id=None):
    """
    toggles user active or not in database

    :param id: database user id
    :return: template users_view.html
    """
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
    """
    adds a user to the database

    :return: either GET: template users_add.html (or) POST: template users_view.html
    """
    form = UserForm()
    if request.method == 'POST':
        now = datetime.datetime.now()

        if request.form["linemanager"] != "":
            firstname, surname = request.form["linemanager"].split(" ")
            line_manager_id = int(s.query(Users).filter_by(first_name=firstname, last_name=surname).first().id)
        else:
            line_manager_id = None

        u = Users(login=request.form["username"],
                  first_name=request.form["firstname"],
                  last_name=request.form["surname"],
                  email=request.form["email"],
                  staff_no=request.form["staff_no"],
                  serviceid=request.form["section"],
                  active=True,
                  line_managerid=line_manager_id)

        s.add(u)
        s.commit()
        print request.form.getlist('userrole')
        for role_id in request.form.getlist('userrole'):
            urr = UserRoleRelationship(userrole_id=int(role_id), user_id=u.id)
            s.add(urr)

        for job_id in request.form.getlist('jobrole'):
            urr = UserJobRelationship(jobrole_id=int(job_id), user_id=u.id)
            s.add(urr)
        s.commit()
        return redirect(url_for('admin.users_view'))

    return render_template("users_add.html", form=form)


@admin.route('/users/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def users_edit(id=None):
    """
    edit user details

    :param id: user id
    :return: either GET: template users_edit.html (or) POST: template users_view.html
    """
    if request.method == 'GET':
        form = UserEditForm()

        user = s.query(Users).filter_by(id=id).first()
        form.username.data = user.login
        form.firstname.data = user.first_name
        form.surname.data = user.last_name
        form.email.data = user.email
        form.staff_no.data = user.staff_no

        line_manager_result = s.query(Users.first_name, Users.last_name).filter_by(id=user.line_managerid).first()
        if line_manager_result is not None:
            form.linemanager.data = line_manager_result[0] + " " + line_manager_result[1]
        else:
            form.linemanager.data = None

        jobrole_ids = [name for (name,) in s.query(UserJobRelationship.jobrole_id).filter_by(user_id=id).all()]

        form.jobrole.choices = s.query(JobRoles.id, JobRoles.job).all()
        form.jobrole.process_data(jobrole_ids)

        userrole_ids = [name for (name,) in s.query(UserRoleRelationship.userrole_id).filter_by(user_id=id).all()]

        form.userrole.choices = s.query(UserRolesRef.id, UserRolesRef.role).all()
        form.userrole.process_data(userrole_ids)

        form.section.choices = s.query(Service.id, Service.name).all()
        print form.section.choices
        form.section.process_data(user.serviceid)

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

        if "staff_no" in request.form:
            staff_no = request.form["staff_no"]
            print "HELLO"
        else:
            staff_no = s.query(Users).filter_by(id=id).first().staff_no

        data = {
            'login': request.form["username"],
            'first_name': request.form["firstname"],
            'last_name': request.form["surname"],
            'email': request.form["email"],
            'line_managerid': line_manager_id,
            'serviceid': request.form["section"],
            'staff_no': staff_no
        }

        s.query(Users).filter_by(id=id).update(data)

        s.commit()

        return redirect(url_for('admin.users_view'))


@admin.route('/jobroles', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def jobroles():
    """
    view and add job roles - a job role is "CLINICAL BIOINFORMATICIAN" or "IT MANAGER" etc
    :return: temlate jobroles.html
    """
    form = JobRoleForm()

    if request.method == 'POST':
        j = JobRoles(job=request.form['job'])
        s.add(j)
        s.commit()

    jobs = s.query(JobRoles).all()

    return render_template("jobroles.html", form=form, data=jobs)


@admin.route('/jobroles/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def jobroles_edit(id=None):
    """
    edit job roles
    :param id: job role id
    :return: either GET: template jobroles_edit.html (or) POST: redirct to jobroles.html
    """
    form = JobRoleForm()
    jobrole = s.query(JobRoles).filter_by(id=id).first()
    form.job.data = jobrole.job

    if request.method == 'POST':
        s.query(JobRoles).filter_by(id=id).update({'job': request.form["job"]})
        s.commit()
        return redirect(url_for('admin.jobroles'))

    return render_template("jobroles_edit.html", form=form, id=id)


@admin.route('/service/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deletejobrole(id=None):
    """
    delete a job role
    :param id: job role db id
    :return: redirect to tempate jobroles.html
    """
    s.query(JobRoles).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.jobroles'))


@admin.route('/service', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def service():
    """
    administer the available services - a service is "Lab Services" "Constitutional" etc
    :return:
    """
    form = ServiceForm()

    if request.method == 'POST':
        n = Service(name=request.form['name'])
        s.add(n)
        s.commit()

    services = s.query(Service).all()

    return render_template("service.html", form=form, data=services)


@admin.route('/service/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def service_edit(id=None):
    """
    edit service
    :param id: service id
    :return:
    """
    form = ServiceForm()
    service = s.query(Service).filter_by(id=id).first()
    form.name.data = service.name

    if request.method == 'POST':
        s.query(Service).filter_by(id=id).update({'name': request.form["name"]})
        s.commit()
        return redirect(url_for('admin.service'))

    return render_template("service_edit.html", form=form, id=id)


@admin.route('/service/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deleteservice(id=None):
    """
    delete a service
    :param id: service id
    :return:
    """
    s.query(Service).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.service'))


@admin.route('/assessmentstatus', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def assessmentstatus():
    """
    adminsiter the assessment status - e.g "Assigned" "Active" etc
    :return:
    """
    form = AssessmentStatusForm()

    if request.method == 'POST':
        a = AssessmentStatusRef(status=request.form['status'])
        s.add(a)
        s.commit()

    assessment_status = s.query(AssessmentStatusRef).all()

    return render_template("assessmentstatus.html", form=form, data=assessment_status)


@admin.route('/assessmentstatus/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def assessmentstatus_edit(id=None):
    """
    edit assessment statuses
    :param id: assessment status id
    :return:
    """
    form = AssessmentStatusForm()
    status = s.query(AssessmentStatusRef).filter_by(id=id).first()
    form.status.data = status.status

    if request.method == 'POST':
        s.query(AssessmentStatusRef).filter_by(id=id).update({'status': request.form["status"]})
        s.commit()
        return redirect(url_for('admin.assessmentstatus'))

    return render_template("assessmentstatus_edit.html", form=form, id=id)


@admin.route('/assessmentstatus/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deleteassessmentstatus(id=None):
    """
    delete assessment status
    :param id: assessment status id
    :return:
    """
    s.query(AssessmentStatusRef).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.assessmentstatus'))


@admin.route('/validityperiods', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def validityperiods():
    """
    administer validity periods - these are how long competences can be valid for in months e.g "6" "12"
    :return:
    """
    form = ValidityPeriodForm()

    if request.method == 'POST':
        m = ValidityRef(months=request.form['months'])
        s.add(m)
        s.commit()

    validity_periods = s.query(ValidityRef).all()

    return render_template("validityperiods.html", form=form, data=validity_periods)


@admin.route('/validityperiods/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def validityperiods_edit(id=None):
    """
    edit validity period
    :param id: validity period id
    :return:
    """
    form = ValidityPeriodForm()
    number_months = s.query(ValidityRef).filter_by(id=id).first()
    form.months.data = number_months.months

    if request.method == 'POST':
        s.query(ValidityRef).filter_by(id=id).update({'months': request.form["months"]})
        s.commit()
        return redirect(url_for('admin.validityperiods'))

    return render_template("validityperiods_edit.html", form=form, id=id)


@admin.route('/validityperiods/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deletevalidityperiod(id=None):
    """
    delet validity period
    :param id: validity period id
    :return:
    """
    s.query(ValidityRef).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.validityperiods'))


@admin.route('/sections', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def sections():
    """
    administer sections - sections are "Health & Safety" "Knowledge & Understanding" etc
    These can be flagged as constant - i.e they should appear on every competence
    :return:
    """
    form = SectionForm()

    if request.method == 'POST':
        if "constant" in request.form:
            constant = True
        else:
            constant = False

        n = Section(name=request.form['name'], constant=constant)
        s.add(n)
        s.commit()

    sections = s.query(Section).all()
    for i in sections:
        print i.constant
    return render_template("sections.html", form=form, data=sections)


@admin.route('/sections/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def sections_edit(id=None):
    """
    edit sections
    :param id: sections id
    :return:
    """
    form = SectionForm()
    section_name = s.query(Section).filter_by(id=id).first()
    form.name.data = section_name.name
    if section_name.constant:
        form.constant.data = "checked"

    if request.method == 'POST':
        print "hello"
        if "constant" in request.form:
            print "here"
            answer = True
        else:
            answer = False

        s.query(Section).filter_by(id=id).update({'name': request.form["name"], 'constant': answer})
        s.commit()
        return redirect(url_for('admin.sections'))

    return render_template("sections_edit.html", form=form, id=id)


@admin.route('/sections/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deletesection(id=None):
    """
    delete section
    :param id: section id
    :return:
    """
    s.query(Section).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.sections'))


@admin.route('/evidencetypes', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def evidencetypes():
    """
    administer evidence types - these are the types of evidence accepted for a subsection of a competence
     e.g "Discussion", "Upload" etc
    :return:
    """
    form = EvidenceTypeForm()

    if request.method == 'POST':
        e = EvidenceTypeRef(type=request.form['type'])
        s.add(e)
        s.commit()

    evidence_types = s.query(EvidenceTypeRef).all()

    return render_template("evidencetypes.html", form=form, data=evidence_types)


@admin.route('/evidencetypes/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def evidencetypes_edit(id=None):
    """
    edit evidence types
    :param id: evidence type if
    :return:
    """
    form = EvidenceTypeForm()
    evidence_type = s.query(EvidenceTypeRef).filter_by(id=id).first()
    form.type.data = evidence_type.type

    if request.method == 'POST':
        s.query(EvidenceTypeRef).filter_by(id=id).update({'type': request.form["type"]})
        s.commit()
        return redirect(url_for('admin.evidencetypes'))

    return render_template("evidencetypes_edit.html", form=form, id=id)


@admin.route('/evidencetypes/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deleteevidencetype(id=None):
    """
    delete evidence type
    :param id: evidence type id
    :return:
    """
    s.query(EvidenceTypeRef).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.evidencetypes'))


@admin.route('/competencetypes', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def competencetypes():
    """
    administer competence types - these are the type of competence e.g. "Scientist", "Equipment" etc
    :return:
    """
    form = CompetenceCategoryForm()

    if request.method == 'POST':
        e = CompetenceCategory(category=request.form['category'])
        s.add(e)
        s.commit()

    competencetypes = s.query(CompetenceCategory).all()

    return render_template("competencetypes.html", form=form, data=competencetypes)


@admin.route('/competencetypes/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def competencetypes_edit(id=None):
    form = CompetenceCategoryForm()
    competencetypes = s.query(CompetenceCategory).filter_by(id=id).first()
    form.category.data = competencetypes.category

    if request.method == 'POST':
        s.query(CompetenceCategory).filter_by(id=id).update({'category': request.form["category"]})
        s.commit()
        return redirect(url_for('admin.competencetypes'))

    return render_template("competencetypes_edit.html", form=form, id=id)


@admin.route('/competencetypes/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deletecompetencetypes(id=None):
    s.query(CompetenceCategory).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.competencetypes'))


@admin.route('/userroles', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def userroles():
    """
    administer user roles - these are the role of the user on stardb e.g. "ADMIN", "USER" etc
    you can only add or change these with overall code changes
    :return:
    """
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


@admin.route('/logs', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def view_logs():
    pass


def transform(text_file_contents):
    return text_file_contents.replace("=", ",")


@admin.route('/bulk_user_upload')
@admin_permission.require(http_exception=403)
def form():
    """
    upload csv file of users to add to database
    csv format must be:
    last name, first name, staffno, job, linemanager (Initials), band

    :return: template bulk_upload_users.html
    """
    return render_template('bulk_upload_users.html')


@app.route('/transform', methods=["POST"])
@admin_permission.require(http_exception=403)
def transform_view():
    """
    method to bulk add users to the database, you need to run twice to 1st add users then add line managers
    to those users
    """
    f = request.files['data_file']
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], f.filename))

    with codecs.open(os.path.join(app.config['UPLOAD_FOLDER'], f.filename), "r", encoding='utf-8',
                     errors='ignore') as csv_input:
        for row in csv_input.readlines():
            clean_row = row.rstrip()
            last, first, staffno, job, linemanager, band = clean_row.split(",")

            line_manager_id = None
            if len(linemanager) == 2:
                one, two = list(linemanager)
                line_manager_query = s.query(Users).filter(Users.first_name.like(one + "%")).filter(
                    Users.last_name.like(two + "%")).first()
                if line_manager_query:
                    line_manager_id = line_manager_query.id
                    print "linemanage_id " + str(line_manager_id)
                    line_manager_role_id = s.query(UserRolesRef).filter_by(role="LINEMANAGER").first().id
                    count = s.query(UserRoleRelationship).filter_by(user_id=line_manager_id).filter_by(
                        userrole_id=line_manager_role_id).count()
                    if count == 0:
                        ur = UserRoleRelationship(user_id=line_manager_id, userrole_id=line_manager_role_id)
                        s.add(ur)
                        s.commit()

            # print s.query(User).filter_by(first)

            result = UserAuthentication().get_username_from_user_detail(first.replace(" ", ""), last)
            if result == "False":
                print first + " " + last
            else:
                result = json.loads(result)
                users = s.query(Users).filter_by(login=result["Username"]).count()
                jobs = s.query(JobRoles).filter_by(job=job).count()
                if jobs == 0:
                    j = JobRoles(job=job.upper())
                    s.add(j)
                    s.flush()
                    s.refresh(j)
                    job_id = j.id
                else:
                    job_id = s.query(JobRoles).filter_by(job=job).first().id

                if users == 0:
                    u = Users(login=result["Username"], first_name=result["Forename"], last_name=result["Surname"],
                              email=result["Email"].lower(), staff_no=staffno, serviceid=None, active=True)
                    s.add(u)
                    s.flush()
                    s.refresh(u)
                    user_id = u.id
                else:
                    user_id = s.query(Users).filter_by(login=result["Username"]).first().id
                    if s.query(Users).filter_by(login=result["Username"]).first().line_managerid == None:
                        data = {'line_managerid': line_manager_id}
                        s.query(Users).filter_by(id=user_id).update(data)
                        s.commit()

                job_roles_user = s.query(UserJobRelationship).filter_by(user_id=user_id).count()
                if job_roles_user == 0:
                    ujr = UserJobRelationship(user_id=user_id, jobrole_id=job_id)
                    s.add(ujr)
                    s.flush()
                    s.refresh(ujr)

                db_roles = s.query(UserRoleRelationship).filter_by(user_id=user_id).count()
                if db_roles == 0:
                    role_id = s.query(UserRolesRef).filter_by(role="USER").first().id
                    ur = UserRoleRelationship(user_id=user_id, userrole_id=role_id)
                    s.add(ur)
                    s.flush()
                    s.refresh(ur)

                band_db = s.query(Users).filter_by(id=user_id).first().band
                print band
                if not band_db:
                    s.query(Users).filter_by(id=user_id).update({'band': band})

    print s.commit()