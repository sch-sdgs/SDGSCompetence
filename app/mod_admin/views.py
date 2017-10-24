from collections import OrderedDict
from sqlalchemy.orm import load_only
from flask import Blueprint
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import admin_permission
from forms import *
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

@admin.route('/questions',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def reassessment_questions():
    form = QuestionsForm()

    if request.method == 'POST':
        q =QuestionsRef(question=request.form['question'])
        s.add(q)
        s.commit()

    questions = s.query(QuestionsRef).all()

    return render_template("questions.html",form=form,data=questions)

@admin.route('/questions/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def reassessment_questions_edit(id=None):
    form=QuestionsForm()
    question = s.query(QuestionsRef).filter_by(id=id).first()
    form.question.data = question.question

    if request.method == 'POST':
        s.query(QuestionsRef).filter_by(id=id).update({'question': request.form["question"]})
        s.commit()
        return redirect(url_for('admin.reassessment_questions'))

    return render_template("questions_edit.html", form=form, id=id)

@admin.route('/questions/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def delete_reassessment_question(id=None):
    s.query(QuestionsRef).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.reassessment_questions'))

@admin.route('/jobroles',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def jobroles():
    form = JobRoleForm()

    if request.method == 'POST':
        j =JobRoles(job=request.form['job'])
        s.add(j)
        s.commit()

    jobs = s.query(JobRoles).all()

    return render_template("jobroles.html",form=form,data=jobs)

@admin.route('/jobroles/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def jobroles_edit(id=None):
    form=JobRoleForm()
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
    s.query(JobRoles).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.jobroles'))


@admin.route('/service',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def service():
    form = ServiceForm()

    if request.method == 'POST':
        n =Service(name=request.form['name'])
        s.add(n)
        s.commit()

    services = s.query(Service).all()

    return render_template("service.html",form=form,data=services)

@admin.route('/service/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def service_edit(id=None):
    form=ServiceForm()
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
    s.query(Service).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.service'))

@admin.route('/assessmentstatus',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def assessmentstatus():
    form = AssessmentStatusForm()

    if request.method == 'POST':
        a = AssessmentStatusRef(status=request.form['status'])
        s.add(a)
        s.commit()

    assessment_status = s.query(AssessmentStatusRef).all()

    return render_template("assessmentstatus.html",form=form,data=assessment_status)

@admin.route('/assessmentstatus/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def assessmentstatus_edit(id=None):
    form=AssessmentStatusForm()
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
    s.query(AssessmentStatusRef).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.assessmentstatus'))

@admin.route('/validityperiods',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def validityperiods():
    form = ValidityPeriodForm()

    if request.method == 'POST':
        m = ValidityRef(months=request.form['months'])
        s.add(m)
        s.commit()

    validity_periods = s.query(ValidityRef).all()

    return render_template("validityperiods.html",form=form,data=validity_periods)

@admin.route('/validityperiods/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def validityperiods_edit(id=None):
    form=ValidityPeriodForm()
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
    s.query(ValidityRef).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.validityperiods'))

@admin.route('/sections',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def sections():
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
    return render_template("sections.html",form=form,data=sections)

@admin.route('/sections/edit/<id>',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def sections_edit(id=None):
    form=SectionForm()
    section_name = s.query(Section).filter_by(id=id).first()
    form.name.data = section_name.name
    if section_name.constant:
        form.constant.data = "checked"

    if request.method == 'POST':
        print "hello"
        if "constant" in request.form:
            print "here"
            answer=True
        else:
            answer=False

        s.query(Section).filter_by(id=id).update({'name': request.form["name"], 'constant': answer})
        s.commit()
        return redirect(url_for('admin.sections'))

    return render_template("sections_edit.html", form=form, id=id)

@admin.route('/sections/delete/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def deletesection(id=None):
    s.query(Section).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.sections'))

@admin.route('/evidencetypes',methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def evidencetypes():
    form = EvidenceTypeForm()

    if request.method == 'POST':
        e = EvidenceTypeRef(type=request.form['type'])
        s.add(e)
        s.commit()

    evidence_types = s.query(EvidenceTypeRef).all()

    return render_template("evidencetypes.html",form=form,data=evidence_types)

@admin.route('/evidencetypes/edit/<id>', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def evidencetypes_edit(id=None):
    form=EvidenceTypeForm()
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
    s.query(EvidenceTypeRef).filter_by(id=id).delete()
    s.commit()
    return redirect(url_for('admin.evidencetypes'))


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


@admin.route('/logs', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def view_logs():
    pass


@admin.route('/application', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def application_admin():
    pass