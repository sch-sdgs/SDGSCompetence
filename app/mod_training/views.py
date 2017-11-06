from flask import Flask, render_template, redirect, request, url_for, session, current_app, Blueprint
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from app.competence import s
from app.models import *
from sqlalchemy.sql.expression import func, and_, or_, case, exists, update
from sqlalchemy.orm import aliased
from werkzeug import secure_filename
import os

training = Blueprint('training', __name__, template_folder='templates')

###########
# Queries #
###########
def get_user(user):
    """
    Method to check if value sent with request is ID, if not the method queries the database and returns the ID

    :param user: user value sent with request
    :return:
    """
    try:
        u_id = int(user)
    except ValueError:
        user_result = s.query(Users).filter(Users.login == user).values(Users.id)
        u_id = 0
        for u in user_result:
            u_id = u[0]
            break

    return u_id

def get_competence_by_user(c_id, u_id):
    """
    Method to get information for competence for a given user

    :param c_id: ID for competence
    :param u_id: ID of user
    :return:
    """
    #get ID for user

    users_alias = aliased(Users)

    #get info for competence (assessments table)
    competence_result = s.query(Assessments).\
        outerjoin(Users, Assessments.signoff_id==Users.id).\
        outerjoin(users_alias, Assessments.trainer_id==Users.id).\
        outerjoin(Subsection).\
        outerjoin(Section).\
        outerjoin(Competence, Subsection.c_id == Competence.id).\
        outerjoin(AssessmentStatusRef, Assessments.status==AssessmentStatusRef.id).\
        outerjoin(EvidenceTypeRef).\
        filter(and_(Assessments.user_id == u_id, Competence.id == c_id)).\
        values(Section.name, Section.constant, Subsection.id, Subsection.name.label('area_of_competence'), Subsection.comments.label('notes'), EvidenceTypeRef.type,
               AssessmentStatusRef.status, (Users.first_name + ' ' + Users.last_name).label('assessor'),
               (users_alias.first_name + ' ' + users_alias.last_name).label('trainer'), Assessments.date_of_training,
               Assessments.date_completed, Assessments.date_expiry, Assessments.comments.label('training_comments'))
    result = {'constant':{}, 'custom':{}}
    for c in competence_result:
        if c.constant:
            d = 'constant'
        else:
            d = 'custom'
        if c.name not in result[d].keys():
            result[d][c.name] = {'complete':0, 'total':0, 'subsections':[]}
        subsection = {'id':c.id,
                      'name':c.area_of_competence,
                      'status':c.status,
                      'evidence_type':c.type,
                      'assessor':filter_for_none(c.assessor),
                      'date_of_completion':filter_for_none(c.date_completed),
                      'notes':filter_for_none(c.notes),
                      'training_comments':filter_for_none(c.training_comments),
                      'trainer':filter_for_none(c.trainer),
                      'date_of_training':filter_for_none(c.date_of_training)}
        if c.date_completed:
            result[d][c.name]['complete'] += 1
        result[d][c.name]['total'] += 1
        subsection_list =  result[d][c.name]['subsections']
        subsection_list.append(subsection)
        result[d][c.name]['subsections'] = subsection_list
    return result

def get_competence_summary_by_user(c_id, u_id):
    """

    :param c_id:
    :param u_id:
    :return:
    """
    competence_result = s.query(Assessments).outerjoin(Users, Users.id == Assessments.user_id).outerjoin(Subsection).\
        outerjoin(Section).outerjoin(Competence, Subsection.c_id == Competence.id).\
        outerjoin(CompetenceDetails, and_(CompetenceDetails.c_id == Competence.id, CompetenceDetails.intro == Competence.current_version)).\
        outerjoin(ValidityRef, CompetenceDetails.validity_period==ValidityRef.id).\
        filter(and_(Users.id == u_id, Competence.id == c_id)). \
        group_by(CompetenceDetails.id).\
        values((Users.first_name + ' ' +  Users.last_name).label('user'),
               CompetenceDetails.title,
               CompetenceDetails.qpulsenum,
               CompetenceDetails.scope,
               ValidityRef.months,
               func.max(Assessments.date_assigned).label('assigned'),
               func.max(Assessments.date_activated).label('activated'),
               case([
                   (s.query(Assessments).\
                       # outerjoin(Subsection, Subsection.id == Assessments.ss_id).\
                       filter(and_(Assessments.user_id == u_id, Subsection.c_id == c_id,
                                   Assessments.date_completed == None)).exists(),
                    None)],
                   else_=func.max(Assessments.date_completed)).label('completed'),
               case([
                   (s.query(Assessments).\
                       # outerjoin(Subsection, Subsection.id == Assessments.ss_id).\
                       filter(and_(Assessments.user_id == u_id, Subsection.c_id == c_id,
                                   Assessments.date_expiry == None)).exists(),
                    None)],
                   else_=func.max(Assessments.date_expiry)).label('expiry'))
    for comp in competence_result:
        return comp

def activate_assessments(c_id, u_id):
    """


    :return:
    """
    for r in s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Active").values(AssessmentStatusRef.id):
        activated = r.id
    for r in s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Assigned").values(AssessmentStatusRef.id):
        assigned = r.id
    print('query')
    statement = s.query(Assessments). \
        filter(Assessments.ss_id == Subsection.id).\
        filter(and_(Assessments.user_id == u_id, Assessments.status == assigned, Subsection.c_id == c_id)).\
        update({Assessments.status:activated, Assessments.date_activated:datetime.date.today()})
    s.commit()
    print(statement)

###########
# Methods #
###########
def filter_for_none(value):
    """
    Method to check if value returned from database is none and replace with '-'

    :param value: the value returned from the database
    :return: if the value is none, the method return '-', else the value from the database is returned
    """
    if not value:
        return '-'
    else:
        return value

###########
#  Views  #
###########

@training.route('/view', methods=['GET', 'POST'])
@login_required
def view_current_competence():
    """


    :return:
    """
    if request.method == 'GET':
        c_id = request.args.get('c_id')
        # c_id = 8
        user = request.args.get('user')
        if not user:
            user = current_user.id

        u_id = get_user(user)
        print(u_id)
        competence_summary = get_competence_summary_by_user(c_id, u_id)
        section_list = get_competence_by_user(c_id, u_id)

        # return template populated
        return render_template('complete_training.html', competence=c_id, u_id=u_id, user=competence_summary.user,
                               number=competence_summary.qpulsenum,
                               title=competence_summary.title, validity=competence_summary.months,
                               scope=competence_summary.scope, section_list=section_list,
                               assigned=competence_summary.assigned, activated = filter_for_none(competence_summary.activated),
                               completed=filter_for_none(competence_summary.completed), expires=filter_for_none(competence_summary.expiry))

@training.route('/select_subsections', methods=['GET', 'POST'])
@login_required
def select_subsections():
    """
    Method to display all subsections for a competence in a checkbox list to allow a number of subsections to be
    selected for activation etc.

    This method can be used in multiple places as it just sends a list of subsection IDs to the action URL which is
    specific to the required action (e.g. assign, upload evidence etc.)

    The method requires the competence ID, user ID (unless the current user is to be used) and the forward action.

    Forward action can be one of the following:

    * assign
    * activate
    * evidence
    * reassess

    This will determine the subsections available for selection and the action completed after selection.

    :return:
    """
    c_id = request.args.get('c_id')

    user = request.args.get('user')
    if not user:
        user = current_user.id
    u_id = get_user(user)

    forward_action = request.args.get('action')
    print(forward_action)

    if request.method == "GET":
        competence_summary = get_competence_summary_by_user(c_id, u_id)
        section_list = get_competence_by_user(c_id, u_id)

        required_status = ""
        heading = "Select the subsections you wish to {}"
        if forward_action == "assign":
            required_status = None
            heading = heading.format("assign")
        elif forward_action == "activate":
            print('here')
            heading = heading.format("activate")
            required_status = "Assigned"
        elif forward_action == "evidence":
            heading = heading.format("associate with this piece of evidence")
            required_status = "Active"
        elif forward_action == "reassess":
            heading = heading.format("reassess")
            required_status = "Complete"

        return render_template('select_subsections.html', competence=c_id, user={'name':competence_summary.user,
                                                                                 'id':u_id},
                               title=competence_summary.title, validity=competence_summary.months, heading=heading,
                               section_list=section_list, required_status=required_status, action=forward_action)
    else:
        pass
    

@training.route('/activate', methods=['GET', 'POST'])
@login_required
def activate_competence():
    """
    Method to change all assessments for a current competence to activated.

    :return:
    """
    u_id = request.args.get('u_id')
    c_id = request.args.get('c_id')

    activate_assessments(c_id, u_id)
    return redirect(url_for('training.view_current_competence', c_id=c_id, user=u_id))


@training.route('/upload')
@login_required
def upload_evidence():
    """
    Method to 
    
    :return: 
    """
    if request.method == 'GET':
        c_id = request.args.get('c_id')
        # c_id = 4
        user = request.args.get('u_id')
        if not user:
            user = current_user.id

        u_id = get_user(user)

        competence_summary = get_competence_summary_by_user(c_id, u_id)
        
        return render_template('upload_evidence.html', competence=c_id, u_id=u_id, user=competence_summary.user,
                               number=competence_summary.qpulsenum,
                               title=competence_summary.title, validity=competence_summary.months)


@training.route('/uploader', methods=['GET', 'POST'])
@login_required
def file_uploader():
    if request.method == 'POST':
        f = request.files['file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
        print(f.filename)
        return 'file uploaded successfully'