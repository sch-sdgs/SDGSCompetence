from flask import Flask, render_template, redirect, request, url_for, session, current_app, Blueprint
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from app.competence import s
from app.models import *
from sqlalchemy.sql.expression import func, and_, or_, case, exists, update
from sqlalchemy.orm import aliased
from werkzeug import secure_filename
import os
from forms import *

training = Blueprint('training', __name__, template_folder='templates')

###########
# Queries #
###########

def get_ss_id_from_assessment(assess_id_list):
    ss_ids_res = s.query(Assessments).filter(Assessments.id.in_(assess_id_list)).values(Assessments.ss_id)
    ss_ids = []

    for ss_id in ss_ids_res:
        ss_ids.append(ss_id.ss_id)

    return ss_ids

def get_competent_users(ss_id_list):
    users = s.query(Users).\
        join(Assessments,Assessments.user_id==Users.id).\
        join(AssessmentStatusRef).\
        filter(AssessmentStatusRef.status=="Complete",
            Assessments.date_expiry>datetime.date.today()).\
        group_by(Users.id).having(func.count(Assessments.ss_id.in_(ss_id_list)) == len(ss_id_list)).\
        values(Users.id, (Users.first_name + ' ' + Users.last_name).label('name'))
    return users

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
        values(Section.name, Subsection.name.label('area_of_competence'), Subsection.comments.label('notes'), EvidenceTypeRef.type,
               AssessmentStatusRef.status, (Users.first_name + ' ' + Users.last_name).label('assessor'),
               (users_alias.first_name + ' ' + users_alias.last_name).label('trainer'), Assessments.date_of_training,
               Assessments.date_completed, Assessments.date_expiry, Assessments.comments.label('training_comments'))
    result = {}
    for c in competence_result:
        if c.name not in result.keys():
            result[c.name] = {'complete':0, 'total':0, 'subsections':[]}
        subsection = {'name':c.area_of_competence,
                      'status':c.status,
                      'evidence_type':c.type,
                      'assessor':filter_for_none(c.assessor),
                      'date_of_completion':filter_for_none(c.date_completed),
                      'notes':filter_for_none(c.notes),
                      'training_comments':filter_for_none(c.training_comments),
                      'trainer':filter_for_none(c.trainer),
                      'date_of_training':filter_for_none(c.date_of_training)}
        if c.date_completed:
            result[c.name]['complete'] += 1
        result[c.name]['total'] += 1
        result[c.name]['subsections'].append(subsection)
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

@training.route('/reassessment', methods=['GET', 'POST'])
@login_required
def reassessment():
    if request.method=='GET':
        c_id = request.args.get('c_id')
        print c_id
        user = request.args.get('user')
        assess_id_list = request.args.get('assess_id_list').split(',')
        if not user:
            user = current_user.id
        u_id = get_user(user)
        competence_summary = get_competence_summary_by_user(c_id, u_id)

        questions = s.query(QuestionsRef).filter(QuestionsRef.active==True)
        data=[]
        for question in questions:
            row={}
            row['id'] = question.id
            row['question'] = question.question
            if question.answer_type == 'Dropdown':
                options = s.query(DropDownChoices).filter(DropDownChoices.question_id==question.id).all()
                row['DropDown'] = []
                for option in options:
                    row['DropDown'].append(option.choice)
            elif question.answer_type == 'Free text':
                row['FreeText'] = True
            elif question.answer_type == 'Date':
                row['Date'] = True
            elif question.answer_type == 'Yes/no':
                row['yesno'] = True
            data.append(row)
        form=Reassessment()
        ss_id_list = get_ss_id_from_assessment(assess_id_list)
        competent_users = get_competent_users(ss_id_list)
        choices=[]
        for user in competent_users:
            choices.append((user.id, user.name))
        form.signoff_id.choices=choices
        return render_template('reassessment.html', data=data, c_id = c_id, user_id=u_id, competence_name=competence_summary.title, form=form, assess_id_list=','.join(assess_id_list))

    elif request.method =='POST':
        print "now posting"
        questions = s.query(QuestionsRef).filter(QuestionsRef.active == True).all()
        print questions
        signoff_id = request.form["signoff_id"]
        print(request.form)
        assess_id_list = request.args.get('assess_id_list').split(',')
        print signoff_id
        reassessment = Reassessments(signoff_id)
        s.add(reassessment)
        s.commit()
        for assess in assess_id_list:
            assess_rel = AssessReassessRel(assess, reassessment.id)
            s.add(assess_rel)
        s.commit()
        for question in questions:
            print(question)
            id = "answer"+str(question.id)
            print id
            answer = request.form.get(id)
            print(answer)
            reassess = ReassessmentQuestions(question_id=question.id, answer=answer, reassessment_id=reassessment.id)
            s.add(reassess)
            s.commit()

        return redirect(url_for('training.view_current_competence', c_id=request.args.get('c_id'), user=request.args.get('u_id')))

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
        user = request.args.get('user')
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