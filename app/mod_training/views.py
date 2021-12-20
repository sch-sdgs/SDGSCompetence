#TODO clean up imports

from flask import Flask, render_template, redirect, request, url_for, session, current_app, Blueprint, \
    send_from_directory, jsonify, Markup
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from app.competence import s,send_mail
from app.models import *
from sqlalchemy.sql.expression import func, and_, or_, case, exists, update, asc
from sqlalchemy.orm import aliased
from dateutil.relativedelta import relativedelta
import os
from app.mod_training.forms import *
import uuid
import json
from collections import OrderedDict
from app.competence import config
import pandas as pd
from plotly.offline import plot
import plotly.graph_objs as go
import datetime
from json import JSONDecodeError

training = Blueprint('training', __name__, template_folder='templates')


@app.context_processor
def utility_processor():
    def get_uploads(evidence_id):
        uploads = s.query(Uploads).filter(Uploads.evidence_id == evidence_id).all()
        return uploads

    return dict(get_uploads=get_uploads)


@app.context_processor
def utility_processor():
    def make_status_label(status):
        if status == "Active":
            html = '<span class="label label-warning">' + status + '</span>'
        elif status == "Assigned":
            html = '<span class="label label-info">' + status + '</span>'
        elif status == "Complete":
            html = '<span class="label label-success">' + status + '</span>'
        elif status == "Failed":
            html = '<span class="label label-danger">' + status + '</span>'
        elif status == "Obsolete":
            html = '<span class="label label-default">' + status + '</span>'
        elif status == "Abandoned":
            html = '<span class="label label-default">' + status + '</span>'
        elif status == "Sign-Off":
            html = '<span class="label label-primary">' + status + '</span>'
        elif status == "Four Year Due":
            html = '<span class="label label-danger">' + status + '</span>'
        elif status == "Not Required":
            html = '<span class="label label-default">' + status + '</span>'
        return html

    return dict(make_status_label=make_status_label)


###########
# Queries #
###########

def get_ss_id_from_assessment(assess_id_list):
    assess_id_list = [ int(x) for x in assess_id_list ]
    ss_ids_res = s.query(Assessments). \
        filter(Assessments.id.in_(assess_id_list)). \
        values(Assessments.ss_id)
    ss_ids = []

    for ss_id in ss_ids_res:
        ss_ids.append(ss_id.ss_id)

    return ss_ids


def get_competent_users(ss_id_list):
    """
    query all users competent in a given competency
    """
    # todo: add competence author to this list
    users = s.query(Users). \
        join(Assessments, Assessments.user_id == Users.id). \
        join(AssessmentStatusRef) \
        .filter(AssessmentStatusRef.status == "Complete") \
        .filter(Assessments.date_expiry > datetime.date.today()) \
        .filter(Assessments.ss_id.in_(ss_id_list)) \
        .filter(Users.active==1) \
        .group_by(Users.id).having(func.count(Assessments.ss_id.in_(ss_id_list)) == len(ss_id_list)). \
        values(Users.id, (Users.first_name + ' ' + Users.last_name).label('name'))
    return users


def get_for_order(c_id, version):
    """
    Gets the 'for order' for a competency, and updates the 'result' dictionary
    :param c_id: ID for competence
    :param version: Version for competence
    :return result: dictionary with some information about the competency
    """
    result = {'constant': OrderedDict(), 'custom': OrderedDict()}

    for_order = s.query(SectionSortOrder). \
        filter(SectionSortOrder.c_id == c_id). \
        order_by(asc(SectionSortOrder.sort_order)). \
        all()

    for x in for_order:
        ### Need to keep Subsection.last == None instead of is None for query to function correctly
        check = s.query(Subsection). \
            filter(Subsection.s_id == x.section_id). \
            filter(and_(Subsection.intro <= version,
                        or_(Subsection.last > version,
                            Subsection.last == None))). \
            count()

        if check > 0:
            if x.section_id_rel.constant == 1:
                result["constant"][x.section_id_rel.name] = OrderedDict()
                result["constant"][x.section_id_rel.name] = {'complete': 0, 'total': 0, 'subsections': []}
            else:
                result["custom"][x.section_id_rel.name] = OrderedDict()
                result["custom"][x.section_id_rel.name] = {'complete': 0, 'total': 0, 'subsections': []}
        else:
            continue

    return result


def get_competence_result(c_id, u_id, version):
    """
    Gets competency information for every competency and converts to dictionary for further queries
    :param c_id: ID for competency
    :param u_id: ID for user
    :param version: Version for competency
    :return competence_result_dictionary: Result of the competency query converted to a dictionary for further processing
    """
    #TODO specify the relationships better (see error) (note: works, just could be formatted better)
    competence_result = s.query(Assessments). \
        join(Subsection, Assessments.ss_id_rel). \
        join(Section, Subsection.s_id_rel). \
        join(SectionSortOrder, Section.sort_order_rel). \
        join(Competence, Subsection.c_id_rel). \
        join(CompetenceDetails, and_(
            Competence.id == CompetenceDetails.c_id,
            CompetenceDetails.intro == version)). \
        join(AssessmentStatusRef, Assessments.status_rel). \
        join(EvidenceTypeRef, Subsection.evidence_rel). \
        filter(AssessmentStatusRef.status != "Obsolete"). \
        filter(and_(Assessments.user_id == u_id,
                    Subsection.c_id == c_id,
                    Competence.id == c_id,
                    Assessments.version == version)). \
        order_by(asc(Section.name)). \
        order_by(asc(Subsection.sort_order)). \
        order_by(asc(SectionSortOrder.sort_order)). \
        values(Assessments.id.label('ass_id'), Section.name, Section.constant, Subsection.id, Assessments.trainer_id,
               Assessments.signoff_id,
               Subsection.name.label('area_of_competence'), Subsection.comments.label('notes'), EvidenceTypeRef.type,
               AssessmentStatusRef.status, Assessments.date_of_training,
               Assessments.date_completed, Assessments.date_expiry, Assessments.comments.label('training_comments'),
               Assessments.version, SectionSortOrder.sort_order)

    competence_result_dictionary = {}
    for c in competence_result:
        competence_result_dictionary[c.ass_id] = {
            "name" : c.name,
            "constant" : c.constant,
            "id" : c.id,
            "trainer_id" : c.trainer_id,
            "signoff_id" : c.signoff_id,
            "area_of_competence" : c.area_of_competence,
            "notes" : c.notes,
            "type" : c.type,
            "status" : c.status,
            "date_of_training" : c.date_of_training,
            "date_completed" : c.date_completed,
            "date_expiry" : c.date_expiry,
            "training_comments" : c.training_comments,
            "version" : c.version,
            "sort_order" : c.sort_order
        }

    return competence_result_dictionary


def parse_competence_result(competence_result, result):
    """
    Performs further queries based on the competency result to populate additional fields (eg. trainer)
    :param competence_result: the result of the competence_result query, converted to a dictionary
    :param result: the result dictionary that has already been processed in the get_for_order() function
    :return result: A dictionary with all necessary information about the competency
    """
    for key, values in competence_result.items():

        if values["constant"]:
            d = "constant"
        else:
            d = "custom"

        if values["name"] not in result[d].keys():
            result[d][values["name"]] = {"complete": 0, "total": 0, "subsections": []}

        evidence = s.query(AssessmentEvidenceRelationship). \
            filter(AssessmentEvidenceRelationship.assessment_id == key). \
            all()

        trainer = "-"
        if values["trainer_id"] is not None:
            q = s.query(Users).filter(Users.id == values["trainer_id"]).first()
            trainer = q.first_name + " " + q.last_name

        assessor = "-"
        if values["signoff_id"] is not None:
            q = s.query(Users).filter(Users.id == values["signoff_id"]).first()
            assessor = q.first_name + " " + q.last_name

        subsection = {"id": key,
                      "name": values["area_of_competence"],
                      "status": values["status"],
                      "evidence_type": values["type"],
                      "assessor": assessor,
                      "date_of_completion": filter_for_none(values["date_completed"]),
                      "notes": filter_for_none(values["notes"]),
                      "training_comments": filter_for_none(values["training_comments"]),
                      "trainer": trainer,
                      "date_of_training": filter_for_none(values["date_of_training"]),
                      "evidence": filter_for_none(evidence)}

        if values["date_completed"]:
            if subsection["status"] in ["Complete", "Not Required", "Four Year Due"]:
                result[d][values["name"]]["complete"] += 1
        result[d][values["name"]]["total"] += 1
        subsection_list = result[d][values["name"]]["subsections"]
        subsection_list.append(subsection)
        result[d][values["name"]]["subsections"] = subsection_list

    return result


def get_competence_by_user(c_id, u_id, version):
    """
    Runs the necessary functions to get information about a given competence for a given user
    08/21 NC - has been split from original method to 3 methods during upgrade to py3
    :param c_id: ID for the competency
    :param u_id: ID for the user
    :param version: Version for the competency
    :return result: Dictionary with all necessary information about the competency
    """
    result = get_for_order(c_id, version)
    competence_result = get_competence_result(c_id, u_id, version)
    result = parse_competence_result(competence_result, result)
    return result


def get_completion_status_counts(c_id, u_id, version):
    competence_result = s.query(Assessments). \
        outerjoin(Users, Users.id == Assessments.user_id). \
        outerjoin(Subsection). \
        outerjoin(Section). \
        outerjoin(Competence, Subsection.c_id == Competence.id). \
        outerjoin(CompetenceDetails, and_(Competence.id == CompetenceDetails.c_id, CompetenceDetails.intro == version)). \
        outerjoin(CompetenceCategory, (CompetenceDetails.category_id == CompetenceCategory.id)). \
        outerjoin(ValidityRef, CompetenceDetails.validity_period == ValidityRef.id). \
        filter(and_(Users.id == u_id, Competence.id == c_id)). \
        filter(Assessments.version == version). \
        values(Assessments.status)

    total_count = 0
    complete_count = 0

    for i in competence_result:
        total_count += 1


def get_competence_summary_by_user(c_id, u_id,version):
    """

    :param c_id:
    :param u_id:
    :return:
    """
    competence_result = s.query(Assessments). \
        outerjoin(Users, Users.id == Assessments.user_id). \
        outerjoin(Subsection). \
        outerjoin(Section). \
        outerjoin(Competence, Subsection.c_id == Competence.id). \
        outerjoin(CompetenceDetails,and_(Competence.id==CompetenceDetails.c_id,CompetenceDetails.intro==version)). \
        outerjoin(CompetenceCategory,(CompetenceDetails.category_id==CompetenceCategory.id)).\
        outerjoin(ValidityRef, CompetenceDetails.validity_period == ValidityRef.id). \
        filter(and_(Users.id == u_id, Competence.id == c_id)). \
        filter(Assessments.version == version).\
        group_by(CompetenceDetails.id). \
        values((Users.first_name + ' ' + Users.last_name).label('user'),
               CompetenceDetails.title,
               Assessments.version,
               func.max(Assessments.status).label('max_status'),
               func.max(Assessments.is_reassessment).label('is_reassessment_max'),
               CompetenceDetails.qpulsenum,
               CompetenceDetails.category_rel,
               CompetenceDetails.scope,
               CompetenceCategory.category,
               Competence.id.label("c_id"),
               ValidityRef.months,
               func.max(Assessments.date_assigned).label('assigned'),
               func.max(Assessments.date_activated).label('activated'),
               func.max(Assessments.due_date).label('due_date'),
               func.min(Assessments.date_expiry).label('expiry'),
               case(
                    [(s.query(Assessments). \
                    outerjoin(Subsection, Subsection.id == Assessments.ss_id). \
                    filter(and_(Assessments.version==version,
                                 Assessments.user_id == u_id,
                                 Subsection.c_id == c_id,
                                 Assessments.status != 9,
                                 Assessments.date_completed == None)).exists(),
                    None)],
                    else_=func.max(Assessments.date_completed)).label('completed'))

    for comp in competence_result:
        return comp


def activate_assessments(ids, u_id,version):
    """
    :return:
    """

    if ids[0] != "":
        ids = [int(x) for x in ids]
    else:
        return False

    activated = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Active").first().id
    assigned = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Assigned").first().id
    not_required = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Not Required").first().id

    s.query(Assessments). \
        filter(and_(Assessments.version==version,
                    Assessments.user_id == u_id,
                    or_(Assessments.status == assigned,
                        Assessments.status == not_required),
                    Assessments.id.in_(ids))). \
        update({Assessments.status: activated,
                Assessments.date_activated: datetime.date.today()},
                synchronize_session='fetch')
    s.commit()
    return True


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
    if request.method == 'GET':

        c_id = request.args.get('c_id')
        version = request.args.get('version')

        current_version = s.query(Competence).filter(Competence.id == c_id).first().current_version
        if int(version) < int(current_version):
            from app.views import index
            return index(message="There is a new version of this competence so it cannot be re-assessed!")


        assess_id_list = request.args.get('assess_id_list').split(',')

        u_id = current_user.database_id
        competence_summary = get_competence_summary_by_user(c_id, u_id,version)

        questions = s.query(QuestionsRef).filter(QuestionsRef.active == True)
        data = []
        for question in questions:
            row = {}
            row['id'] = question.id
            row['question'] = question.question
            if question.answer_type == 'Dropdown':
                options = s.query(DropDownChoices).filter(DropDownChoices.question_id == question.id).all()
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
        form = Reassessment()
        ss_id_list = get_ss_id_from_assessment(assess_id_list)

        choices = []

        competent_users = get_competent_users(ss_id_list)
        for user in competent_users:
            if user.id != current_user.database_id:
                choices.append((user.id, user.name))
        # todo append competence author
        # add admins to reassessment authorisers
        authoriser_config = config["AUTHORISER"].split(",")
        if "ADMIN" in authoriser_config:
            admin_users = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
                UserRolesRef.role == "ADMIN").filter(Users.active==1).all()
            for i in admin_users:
                check_name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name
                id = i.user_id_rel.id
                if (id, check_name) not in choices:
                    name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (ADMIN)"
                    if id != current_user.database_id:
                        choices.append((id, name))

        choices.sort(key=lambda a: a[1])
        form.signoff_id.choices = choices
        return render_template('reassessment.html', data=data, c_id=c_id, user_id=u_id,
                               competence_name=competence_summary.title, form=form,
                               assess_id_list=','.join(assess_id_list),version=version)

    elif request.method == 'POST':
        questions = s.query(QuestionsRef).filter(QuestionsRef.active == True).all()

        signoff_id = request.form["signoff_id"]

        assess_id_list = request.args.get('assess_id_list').split(',')

        reassessment = Reassessments(signoff_id, 0)
        s.add(reassessment)
        s.commit()
        for assess in assess_id_list:
            assess_rel = AssessReassessRel(assess, reassessment.id)
            s.add(assess_rel)
        s.commit()
        for question in questions:

            id = "answer" + str(question.id)

            answer = request.form.get(id)

            reassess = ReassessmentQuestions(question_id=question.id, answer=answer, reassessment_id=reassessment.id)
            s.add(reassess)

            s.query(Reassessments).filter(Reassessments.id == reassessment.id).update({"date_completed":datetime.date.today()})

            s.commit()

        return redirect(
            url_for('training.view_current_competence', version= request.args.get('version'),c_id=request.args.get('c_id'), user=request.args.get('u_id')))


@training.route('/reassessment_view/<int:reassess_id>', methods=['GET', 'POST'])
@login_required
def reassessment_view(reassess_id=None):
    """
    Renders reassessment page for a given competency
    """
    reassessment = s.query(Reassessments). \
        join(AssessReassessRel). \
        filter(Reassessments.id==reassess_id). \
        group_by(AssessReassessRel.reassess_id). \
        first()

    return render_template('reassessment_view.html',reassessment=reassessment)


@training.route('/view', methods=['GET', 'POST'])
@login_required
def view_current_competence():
    """


    :return:
    """
    if request.method == 'GET':
        c_id = request.args.get('c_id')
        version = request.args.get('version')
        u_id = current_user.database_id

        competence_summary = get_competence_summary_by_user(c_id, u_id,version)


        section_list = get_competence_by_user(c_id, u_id,version)
        statuses = []

        for section_heading in section_list['custom']:
            for subsection in section_list['custom'][section_heading]['subsections']:
                if subsection['status'] not in statuses:
                    statuses.append(subsection['status'])

        print("statuses")
        print(statuses)

        reassessments = s.query(Reassessments). \
            join(AssessReassessRel). \
            join(Assessments). \
            join(AssessmentStatusRef). \
            join(Subsection). \
            join(Competence). \
            filter(AssessmentStatusRef.status != "Obsolete"). \
            filter(Assessments.user_id==u_id). \
            filter(Competence.id==c_id). \
            filter(Assessments.version==version). \
            all()

        # Note: you need to use the bad syntax 'C.f == None' for the query to work
        detail_query = s.query(CompetenceDetails). \
            join(Competence, CompetenceDetails.competence). \
            filter(CompetenceDetails.c_id == c_id). \
            filter(CompetenceDetails.intro <= version). \
            filter(or_(CompetenceDetails.last >= version,
                       CompetenceDetails.last == None)). \
            first()
        detail_id = detail_query.id

        videos = s.query(Videos).filter(Videos.c_id==detail_id).all()

        four_year_check = s.query(Assessments). \
            join(Subsection). \
            join(Competence). \
            join(AssessmentStatusRef). \
            filter(Assessments.user_id==u_id). \
            filter(AssessmentStatusRef.status=="Four Year Due"). \
            filter(Competence.id==c_id). \
            count()

        ### Add a check for competencies which will reach 4 year due within a month
        #TODO update this to take all multiples of 4 years
        todays_date = datetime.date.today()
        four_year_check += s.query(Assessments). \
            join(Subsection). \
            join(Competence). \
            filter(Assessments.user_id==u_id). \
            filter(Assessments.date_completed < todays_date + relativedelta(months=-48)). \
            filter(Competence.id==c_id). \
            count()

        # return template populated
        return render_template('complete_training.html', competence=c_id, u_id=u_id, user=competence_summary.user,
                               number=competence_summary.qpulsenum,
                               title=competence_summary.title, validity=competence_summary.months,
                               scope=competence_summary.scope, section_list=section_list,
                               assigned=competence_summary.assigned,
                               due_date=competence_summary.due_date,
                               activated=filter_for_none(competence_summary.activated),
                               completed=filter_for_none(competence_summary.completed),
                               expires=filter_for_none(competence_summary.expiry),
                               version=competence_summary.version, statuses=statuses,
                               reassessments=reassessments,videos=videos,four_year_check=four_year_check)


@training.route('/make_inactive')
@login_required
def mark_not_required(c_id=None, s_ids=None, version=None):
    """
    Method to request certain subsections are marked as not required
    """
    form = MarkNotRequired()
    ass_ids = json.loads(request.form["ids"])
    ss_id_list = get_ss_id_from_assessment(ass_ids)
    competent_users = get_competent_users(ss_id_list)

    # deal with authorisers
    # Add competent staff to authorisors
    authoriser_config = config["AUTHORISER"].split(",")
    authoriser_choices = []
    if "COMPETENT_STAFF" in authoriser_config:
        for user in competent_users:
            authoriser_choices.append((user.id, user.name))
    if "TRAINER" in authoriser_config:
        trainers = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
            UserRolesRef.role == "TRAINER").all()
        for i in trainers:
            id = i.user_id_rel.id
            name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (TRAINER)"
            authoriser_choices.append((id, name))
    if "ADMIN" in authoriser_config:
        admin_users = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
            UserRolesRef.role == "ADMIN").filter(Users.active == 1).all()
        for i in admin_users:
            check_name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name
            id = i.user_id_rel.id
            if (id, check_name) not in authoriser_choices:
                name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (ADMIN)"
                authoriser_choices.append((id, name))

    authoriser_choices.sort(key=lambda a: a[1])
    form.assessor.choices = authoriser_choices

    u_id = current_user.database_id

    competence_summary = get_competence_summary_by_user(c_id, u_id, version)
    names = s.query(Assessments).filter(Assessments.id.in_(s_ids)).all()

    return render_template('make_inactive.html', c_id=c_id, u_id=u_id, user=competence_summary.user, version=version,
                           number=competence_summary.qpulsenum,
                           title=competence_summary.title, validity=competence_summary.months, form=form, s_ids=s_ids,
                           s_names=names)


@training.route('/upload')
@login_required
def upload_evidence(c_id=None, s_ids=None,version=None):
    """
    Renders evidence upload page
    """

    ass_ids = json.loads(request.form["ids"])

    form = UploadEvidence()

    ss_id_list = get_ss_id_from_assessment(ass_ids)
    competent_users = get_competent_users(ss_id_list)

    # deal with trainers
    trainer_config = config["TRAINER"].split(",")
    trainer_choices = []
    if "COMPETENT_STAFF" in trainer_config:
        for user in competent_users:
            trainer_choices.append((user.id, user.name))
    if "TRAINER" in trainer_config:
        trainers = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
            UserRolesRef.role == "TRAINER").all()
        for i in trainers:
            id = i.user_id_rel.id
            name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (TRAINER)"
            trainer_choices.append((id, name))
    if "ADMIN" in trainer_config:
        admin_users = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
            UserRolesRef.role == "ADMIN").filter(Users.active==1).all()
        for i in admin_users:
            check_name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name
            id = i.user_id_rel.id
            if (id, check_name) not in trainer_choices:
                id = i.user_id_rel.id
                name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (ADMIN)"
                trainer_choices.append((id, name))

    ss_id_list = get_ss_id_from_assessment(ass_ids)
    competent_users = get_competent_users(ss_id_list)

    #deal with authorisers
    #Add competent staff to authorisors
    authoriser_config = config["AUTHORISER"].split(",")
    authoriser_choices = []
    if "COMPETENT_STAFF" in authoriser_config:
        for user in competent_users:
            authoriser_choices.append((user.id, user.name))
    if "TRAINER" in authoriser_config:
        trainers = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
            UserRolesRef.role == "TRAINER").all()
        for i in trainers:
            id = i.user_id_rel.id
            name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (TRAINER)"
            authoriser_choices.append((id, name))
    if "ADMIN" in authoriser_config:
        admin_users = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
            UserRolesRef.role == "ADMIN").filter(Users.active==1).all()
        for i in admin_users:
            check_name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name
            id = i.user_id_rel.id
            if (id, check_name) not in authoriser_choices:
                name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (ADMIN)"
                authoriser_choices.append((id, name))

    if "COMPETENCY_AUTHORISER" in authoriser_config:
        trainers = s.query(UserRoleRelationship).join(UserRolesRef).join(Users).filter(
            UserRolesRef.role == "COMPETENCY_AUTHORISER").all()
        for i in trainers:
            id = i.user_id_rel.id
            name = i.user_id_rel.first_name + " " + i.user_id_rel.last_name + " (COMPETENCY_AUTHORISER)"
            authoriser_choices.append((id, name))


    #sub_section_name = ass.ss_id_rel.name
    authoriser_choices.sort(key=lambda a: a[1])
    form.assessor.choices = authoriser_choices

    trainer_choices.sort(key=lambda a: a[1])
    form.trainer.choices = trainer_choices


    u_id = current_user.database_id

    competence_summary = get_competence_summary_by_user(c_id, u_id,version)
    names = s.query(Assessments).filter(Assessments.id.in_(s_ids)).all()
    return render_template('upload_evidence.html', c_id=c_id, u_id=u_id, user=competence_summary.user, version=version,
                           number=competence_summary.qpulsenum,
                           title=competence_summary.title, validity=competence_summary.months, form=form, s_ids=s_ids, s_names=names)

@training.route('/reassessment_reject/<int:id>', methods=['GET', 'POST'])
def reject_reassessment(id=None):

    data = {
        'is_correct':0,
        'comments':request.form['feedback']
    }

    s.query(Reassessments).filter(Reassessments.id == id).update(data)
    s.commit()

    return redirect('/index')

@training.route('/reassessment_accept/<int:id>', methods=['GET', 'POST'])
def accept_reassessment(id=None):
    ###this method needs to do all the updating to the assessemenst to give a new expiry date
    authoriser = s.query(Reassessments).filter(Reassessments.signoff_id==current_user.database_id).filter(Reassessments.id==id).count()
    if authoriser == 1:

        data = {
            'is_correct':1,
            'comments':'Accepted'
        }

        s.query(Reassessments).filter(Reassessments.id == id).update(data)
        s.commit()

        for i in s.query(Reassessments).join(AssessReassessRel).join(Assessments).filter(Reassessments.id == id).all():
            for j in i.assessments_rel:
                current_version = j.assess_rel.ss_id_rel.c_id_rel.current_version
                for detail in j.assess_rel.ss_id_rel.c_id_rel.competence_detail:
                    if detail.intro <= current_version:
                        new_expiry = i.date_completed + relativedelta(months=detail.validity_rel.months)

                data = {
                    'date_expiry':new_expiry
                }
                s.query(Assessments).filter(Assessments.id == j.assess_id).update(data)

        s.commit()

    return redirect('/index')



@training.route('/uploads/<path:filename>/<path:alias>', methods=['GET', 'POST'])
def download(filename, alias):
    #    uploads = os.path.join(current_app.root_path, app.config['UPLOAD_FOLDER'])
    uploads = app.config["UPLOAD_FOLDER"]
    return send_from_directory(directory=uploads, path=filename, as_attachment=True, attachment_filename=alias)

@training.route('/signoff/<int:assess_id>', methods=['GET', 'POST'])
@login_required
def signoff(assess_id):
    ass = s.query(Assessments).filter(Assessments.id == assess_id).first()
    competence_id = ass.ss_id_rel.c_id

    if request.method == "GET":

        # check if user has evidence for this competence to stop cheating
        count = s.query(AssessmentEvidenceRelationship).filter(
            AssessmentEvidenceRelationship.assessment_id == assess_id).count()

        if count != 0:
            form = SignOffForm()
            ss_id_list = get_ss_id_from_assessment([assess_id])
            competent_users = get_competent_users(ss_id_list)

            sub_section_name = ass.ss_id_rel.name

            choices = []
            for user in competent_users:
                choices.append((user.id, user.name))

            #append competence author
            #TODO append competence author code is here!
            author = s.query(Users).filter(Users.id == ass.ss_id_rel.c_id_rel.competence_detail[0].creator_id).first()
            choices.append((author.id,author.first_name + " " + author.last_name))

            form.trainer.choices = choices
            form.assessor.choices = choices
            return render_template('submit_for_sign_off.html', form=form, assess_id=assess_id,
                                   sub_section_name=sub_section_name)

        else:
            return redirect(url_for('training.view_current_competence') + "?c_id=" + str(competence_id))

    if request.method == "POST":

        status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Sign-Off").first().id

        data = {'trainer_id': request.form['trainer'],
                'date_of_training': request.form['date'],
                'signoff_id': request.form['assessor'],
                'status': status_id,
                }
        s.query(Assessments).filter(Assessments.id==assess_id).update(data)
        s.commit()

@training.route('/self_complete/<int:assess_id>', methods=['GET', 'POST'])
@login_required
def self_complete(assess_id):
    c_id = request.args.get('c_id')
    version = request.args.get('version')
    status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Complete").first().id

    query = s.query(Assessments).filter(Assessments.id == assess_id).first()

    for detail in query.ss_id_rel.c_id_rel.competence_detail:
        if detail.intro <= query.version:
            months_valid = detail.validity_rel.months

    data = {'trainer_id': current_user.database_id,
            'date_of_training': datetime.date.today(),
            'date_completed': datetime.date.today(),
            'date_expiry': datetime.date.today() + relativedelta(months=months_valid),
            'signoff_id': current_user.database_id,
            'status': status_id,
            }

    s.query(Assessments).filter(Assessments.id == assess_id).update(data)
    s.commit()
    return redirect(url_for('training.view_current_competence')+"?c_id="+str(c_id)+"&version="+str(version))

@training.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():

    c_id = request.args["c_id"]
    version = request.args["version"]
    #find assessments records for this competence for current user
    assessments = s.query(Assessments).join(Subsection).filter(and_(Subsection.c_id == c_id,Assessments.user_id==current_user.database_id, Assessments.version==version)).all()

    for assessment in assessments:
        obsolete_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status=="Obsolete").first().id
        data = {'status': obsolete_id, 'due_date': None, 'date_expiry': None}

        s.query(Assessments).filter_by(id=assessment.id).update(data)
        s.commit()

        ### need to remove expiry date

    return json.dumps({'success': True})



@training.route('/abandon', methods=['GET', 'POST'])
@login_required
def abandon():
    c_id = request.args["c_id"]
    version = request.args["version"]
    abandon_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status=="Abandoned").first().id
    data = {'status':abandon_id}
    assessments = s.query(Assessments).join(Subsection).filter(and_(Subsection.c_id == c_id, Assessments.version == version, Assessments.user_id == current_user.database_id)).all()
    for assessment in assessments:
        s.query(Assessments).filter_by(id=assessment.id).update(data)
    try:
        s.commit()
        return jsonify({"success": True})
    except:
        pass


@training.route('/signoff_evidence/<string:action>/<int:evidence_id>', methods=['GET', 'POST'])
@login_required
def signoff_evidence(evidence_id,action):
    """
    Accept or reject evidence OR inactivation requests
    """
    evidence_type = int(s.query(Evidence). \
        filter(Evidence.id == evidence_id). \
        first(). \
        evidence_type_id)

    if evidence_type == 6: #inactivation request
        if action == "accept":
            data = {
                'is_correct': 1,
                'comments': request.form['comments'],
            }
            s.query(Evidence). \
                filter(Evidence.id == evidence_id). \
                update(data)
            status = s.query(AssessmentStatusRef). \
                filter(AssessmentStatusRef.status == "Not Required"). \
                first(). \
                id
            date = None
        elif action == "reject":
            data = {
                'is_correct': 0,
                'comments': request.form["comments"]
            }
            s.query(Evidence). \
                filter(Evidence.id == evidence_id). \
                update(data)
            status = s.query(AssessmentStatusRef). \
                filter(AssessmentStatusRef.status == "Assigned"). \
                first(). \
                id
            date = None

        assessments_to_update = s.query(AssessmentEvidenceRelationship). \
            filter(AssessmentEvidenceRelationship.evidence_id == evidence_id). \
            all()

        for assessment in assessments_to_update:
            query = s.query(Assessments). \
                filter(Assessments.id == assessment.assessment_id). \
                first()
            for detail in query.ss_id_rel.c_id_rel.competence_detail:
                if detail.intro <= query.version:
                    months_valid = detail.validity_rel.months
            try:
                date_completed_info = request.form["completed_date"]
                date_completed = datetime.datetime.strptime(date_completed_info, "%Y-%m-%d")
            except:
                date_completed = datetime.datetime.now()
            data = {
                'date_completed': date_completed,
                'status': status,
                'date_expiry': date_completed + relativedelta(months=months_valid)
            }
            s.query(Assessments). \
                filter(Assessments.id == assessment.assessment_id). \
                update(data)
            s.commit()

        send_mail(query.user_id, "Inactivation Request Reviewed",
                  "Your inactivation request was reviewed by <b>" + current_user.full_name + "</b>")

        return redirect(url_for('index'))

    else:
        if action == "accept":
            data = {
                'is_correct': 1,
                'comments': request.form["comments"],
            }
            s.query(Evidence). \
                filter(Evidence.id == evidence_id). \
                update(data)
            status = s.query(AssessmentStatusRef). \
                filter(AssessmentStatusRef.status == "Complete"). \
                first(). \
                id
            date = datetime.date.today()
        elif action == "reject":
            data = {
                'is_correct': 0,
                'comments': request.form["comments"],
            }
            s.query(Evidence). \
                filter(Evidence.id == evidence_id). \
                update(data)
            status = s.query(AssessmentStatusRef). \
                filter(AssessmentStatusRef.status == "Failed"). \
                first(). \
                id
            date = None

        assessments_to_update = s.query(AssessmentEvidenceRelationship). \
            filter(AssessmentEvidenceRelationship.evidence_id == evidence_id). \
            all()

        for assessment in assessments_to_update:
            query = s.query(Assessments). \
                filter(Assessments.id == assessment.assessment_id). \
                first()

            for detail in query.ss_id_rel.c_id_rel.competence_detail:
                if detail.intro <= query.version:
                    months_valid = detail.validity_rel.months

            try:
                date_completed_info = request.form["completed_date"]
                date_completed = datetime.datetime.strptime(date_completed_info, "%Y-%m-%d")
            except:
                date_completed = datetime.datetime.now()
            data = {
                'date_completed': date_completed,
                'status': status,
                'date_expiry': date_completed + relativedelta(months=months_valid)
            }

            s.query(Assessments).filter(Assessments.id ==assessment.assessment_id).update(data)
            s.commit()

        send_mail(query.user_id, "Evidence Reviewed",
              "Your evidence was reviewed by <b>" + current_user.full_name + "</b>")

        return redirect(url_for('index'))


@training.route('/process_evidence', methods=['GET', 'POST'])
@login_required
def process_evidence():
    """
    Method which processes competency evidence
    """
    s_ids = request.args.get('s_ids').split(",")
    c_id = request.args.get('c_id')
    version = request.args.get('version')
    status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Sign-Off").first().id

    evidence_type = s.query(EvidenceTypeRef).filter(EvidenceTypeRef.id == int(request.form['evidence_type'])).first().type
    four_year_status = request.form.getlist('four_year_status')

    if evidence_type == "Case":
        evidence = request.form.getlist('case')
        result = request.form.getlist('result')
        for i in zip(evidence,result):
            e = Evidence(is_correct=None, signoff_id=request.form['assessor'], date=datetime.date.today(),
                         evidence=i[0], result=i[1],
                         comments=None, evidence_type_id=request.form["evidence_type"])
            s.add(e)
            s.commit()
            for assess_id in s_ids:
                er = AssessmentEvidenceRelationship(assess_id, e.id)
                s.add(er)
    else:
        if evidence_type == "Upload":
            evidence = "Upload"
            result = None

        if evidence_type == "Discussion":
            evidence = request.form['evidence_discussion']
            result = None

        if evidence_type == "Observation":
            evidence = request.form['evidence_observation']
            result = None

        if evidence_type == "Completed competence panel":
            evidence = "Upload"
            result = None

        e = Evidence(is_correct=None, signoff_id=request.form['assessor'], date=datetime.date.today(),
                     evidence=evidence, result=result,
                     comments=None, evidence_type_id=request.form["evidence_type"])
        s.add(e)
        s.commit()
        for assess_id in s_ids:
            er = AssessmentEvidenceRelationship(assess_id, e.id)
            s.add(er)

        if four_year_status == 1:
            # Create a new reassessment
            # Update assess reassess rel
            # Update assess evidence rel
            pass

    s.commit()

    status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Sign-Off").first().id

    data = {'trainer_id': request.form['trainer'],
            'date_of_training': request.form['datetrained'],
            'signoff_id': request.form['assessor'],
            'status': status_id,
            }

    for assess_id in s_ids:
        s.query(Assessments).filter(Assessments.id == int(assess_id)).update(data)

    s.commit()

    uploaded_files = request.files.getlist("file")

    if len(uploaded_files) > 0:

        for f in uploaded_files:
            # this prevents an additional blank file being uploaded
            if f.content_type == 'application/octet-stream':
                continue

            # generate uuid in case someone uploads file of same name and it's actually different - store real name in db
            upload_filename = str(uuid.uuid4())
            f.stream.seek(0)
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], upload_filename))
            u = Uploads(upload_filename, f.filename, current_user.database_id, e.id)
            s.add(u)
        s.commit()

    # send_mail(request.form['assessor'], "Evidence awaiting your review",
    #           "You have evidence from <b>" + current_user.full_name + "</b> awaiting your review")
    send_mail(request.form['assessor'], "Evidence awaiting your review", "")
    # send_mail(request.form['assessor'], "Evidence awaiting your review", "Your evidence was reviewed by <b>" + current_user.full_name + "</b>")

    return redirect(url_for('training.view_current_competence')+"?version="+str(version)+"&c_id="+str(c_id))


@training.route('/process_inactivation_request', methods=['GET', 'POST'])
@login_required
def process_inactivation_request():
    """
    Method which handles the processing of the inactivation request
    """
    s_ids = request.args.get('s_ids').split(",")
    c_id = request.args.get('c_id')
    version = request.args.get('version')

    ### Save the not required request as evidence so it can be handled for approval

    # create evidence
    evidence_type = s.query(EvidenceTypeRef). \
        filter(EvidenceTypeRef.type == "Inactivation Request"). \
        first()
    evidence = request.form['inactivation_reason']
    result = None
    e = Evidence(is_correct=None, signoff_id=request.form['assessor'], date=None,
                 evidence=evidence, result=result, comments=None, evidence_type_id = evidence_type.id)
    s.add(e)
    s.commit()

    #update assessment evidence relationship
    for assess_id in s_ids:
        er = AssessmentEvidenceRelationship(assess_id, e.id)
        s.add(er)
    s.commit()

    #update assessment status
    status_id = s.query(AssessmentStatusRef). \
        filter(AssessmentStatusRef.status == "Sign-Off"). \
        first(). \
        id
    data = {'signoff_id': request.form['assessor'],
            'status': status_id}
    for assess_id in s_ids:
        s.query(Assessments). \
            filter(Assessments.id == int(assess_id)). \
            update(data)
    s.commit()

    #send email to assessor
    send_mail(request.form['assessor'], "Inactivation request awaiting your review", "")

    #Redirect to competency page
    return redirect(url_for('training.view_current_competence') + "?version=" + str(version) + "&c_id=" + str(c_id))


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
    * mark as not required
    * four year reassess

    This will determine the subsections available for selection and the action completed after selection.

    :return:
    """
    c_id = request.args.get('c_id')
    version = request.args.get('version')
    u_id = current_user.database_id

    forward_action = request.args.get('action')

    form = SubSectionsForm()

    if request.method == "GET":
        competence_summary = get_competence_summary_by_user(c_id, int(u_id),version)
        section_list = get_competence_by_user(c_id, int(u_id),version)

        required_status = ""
        heading = "{} Subsections"
        if forward_action == "assign":
            required_status = None
            heading = heading.format("assign")
        elif forward_action == "activate":
            heading = heading.format("Activate")
            required_status = ["Assigned", "Not Required"]
        elif forward_action == "evidence":
            heading = heading.format("Assign Evidence to")
            required_status = ["Active","Failed","Complete","Sign-Off", "Not Required"]
        elif forward_action == "reassess":
            heading = heading.format("Reassess")
            required_status = ["Complete"]
        elif forward_action == "make_inactive":
            heading = heading.format("Mark As Not Required")
            required_status = ["Active", "Assigned", "Failed", "Sign-Off"]
        elif forward_action == "four_year_reassess":
            heading = heading.format("Four Year Reassess")

        return render_template('select_subsections.html', competence=c_id, user={'name': competence_summary.user,
                                                                                 'id': u_id},
                               title=competence_summary.title, validity=competence_summary.months, heading=heading,
                               section_list=section_list, required_status=required_status, action=forward_action,
                               form=form,version=version)
    else:

        ids = form.ids.data.replace('"', '').replace('[', '').replace(']', '').split(',')
        if forward_action == "assign":
            pass
        elif forward_action == "activate":
            result = activate_assessments(ids, u_id,version)
            if result == False:
                return redirect(url_for('training.view_current_competence', c_id=c_id, user=u_id, version=version))

        elif forward_action == "make_inactive":
            comp_section_ids = []
            section_list = get_competence_by_user(c_id, int(u_id), version)
            for i in list(section_list["custom"].items())[0][1]["subsections"]:
                comp_section_ids.append(str(i['id']))

            """Check if user has selected every subsection in the competency"""
            id_check = all(id in ids for id in comp_section_ids)
            if id_check is True:
                message = "You cannot set an entire competency to not required."
                competence_summary = get_competence_summary_by_user(c_id, int(u_id), version)
                section_list = get_competence_by_user(c_id, int(u_id), version)
                required_status = ""
                heading = "Select Subsections"
                if forward_action == "assign":
                    required_status = None
                    heading = heading.format("assign")
                elif forward_action == "activate":
                    heading = heading.format("Activate")
                    required_status = ["Assigned"]
                elif forward_action == "evidence":
                    heading = heading.format("Assign Evidence to")
                    required_status = ["Active", "Failed", "Complete", "Sign-Off", "Not Required"]
                elif forward_action == "reassess":
                    heading = heading.format("Reassess")
                    required_status = ["Complete"]
                elif forward_action == "make_inactive":
                    heading = heading.format("Mark As Not Required")
                    required_status = ["Not Required"]

                return render_template('select_subsections.html', competence=c_id,
                                       user={'name': competence_summary.user,
                                             'id': u_id},
                                       title=competence_summary.title, validity=competence_summary.months,
                                       heading=heading,
                                       section_list=section_list, required_status=required_status,
                                       action=forward_action,
                                       form=form, version=version, message=message)

            else:
                try:
                    return mark_not_required(c_id, ids, version)
                except JSONDecodeError:
                    message = "You must select at least one active subsection!"
                    competence_summary = get_competence_summary_by_user(c_id, int(u_id), version)
                    section_list = get_competence_by_user(c_id, int(u_id), version)
                    required_status = ""
                    heading = "Select Subsections"
                    if forward_action == "assign":
                        required_status = None
                        heading = heading.format("assign")
                    elif forward_action == "activate":
                        heading = heading.format("Activate")
                        required_status = ["Assigned"]
                    elif forward_action == "evidence":
                        heading = heading.format("Assign Evidence to")
                        required_status = ["Active", "Failed", "Complete", "Sign-Off", "Not Required"]
                    elif forward_action == "reassess":
                        heading = heading.format("Reassess")
                        required_status = ["Complete"]
                    elif forward_action == "make_inactive":
                        heading = heading.format("Mark As Not Required")
                        required_status = ["Not Required"]

                    return render_template('select_subsections.html', competence=c_id,
                                           user={'name': competence_summary.user,
                                                 'id': u_id},
                                           title=competence_summary.title, validity=competence_summary.months,
                                           heading=heading,
                                           section_list=section_list, required_status=required_status,
                                           action=forward_action,
                                           form=form, version=version, message=message)

        elif forward_action == "evidence":
            try:
                return upload_evidence(c_id, ids,version)
            except JSONDecodeError:
                message = "You must select at least one active subsection!"
                competence_summary = get_competence_summary_by_user(c_id, int(u_id), version)
                section_list = get_competence_by_user(c_id, int(u_id), version)

                required_status = ""
                heading = "Select Subsections"
                if forward_action == "assign":
                    required_status = None
                    heading = heading.format("assign")
                elif forward_action == "activate":
                    heading = heading.format("Activate")
                    required_status = ["Assigned"]
                elif forward_action == "evidence":
                    heading = heading.format("Assign Evidence to")
                    required_status = ["Active", "Failed", "Complete", "Sign-Off", "Not Required"]
                elif forward_action == "reassess":
                    heading = heading.format("Reassess")
                    required_status = ["Complete"]
                elif forward_action == "make_inactive":
                    heading = heading.format("Mark As Not Required")
                    required_status = ["Not Required"]

                return render_template('select_subsections.html', competence=c_id,
                                       user={'name': competence_summary.user,
                                             'id': u_id},
                                       title=competence_summary.title, validity=competence_summary.months,
                                       heading=heading,
                                       section_list=section_list, required_status=required_status,
                                       action=forward_action,
                                       form=form, version=version, message=message)

        elif forward_action == "four_year_reassess":
            try:
                comp_section_ids = []
                section_list = get_competence_by_user(c_id, int(u_id), version)
                for i in list(section_list["custom"].items())[0][1]["subsections"]:
                    if i['status'] == "Four Year Due":
                        comp_section_ids.append(str(i['id']))
                print(comp_section_ids)
                print(ids)
                """Check if user has selected every complete subsection in the competency"""
                id_check = all(id in ids for id in comp_section_ids)
                if id_check is True:
                    return upload_evidence(c_id, ids,version)
                else:
                    message = "You must reassess the entire competency."
                    competence_summary = get_competence_summary_by_user(c_id, int(u_id), version)
                    section_list = get_competence_by_user(c_id, int(u_id), version)
                    required_status = ""
                    heading = "Select Subsections"
                    if forward_action == "assign":
                        required_status = None
                        heading = heading.format("assign")
                    elif forward_action == "activate":
                        heading = heading.format("Activate")
                        required_status = ["Assigned"]
                    elif forward_action == "evidence":
                        heading = heading.format("Assign Evidence to")
                        required_status = ["Active", "Failed", "Complete", "Sign-Off", "Not Required"]
                    elif forward_action == "reassess":
                        heading = heading.format("Reassess")
                        required_status = ["Complete"]
                    elif forward_action == "make_inactive":
                        heading = heading.format("Mark As Not Required")
                        required_status = ["Not Required"]

                    return render_template('select_subsections.html', competence=c_id,
                                           user={'name': competence_summary.user,
                                                 'id': u_id},
                                           title=competence_summary.title, validity=competence_summary.months,
                                           heading=heading,
                                           section_list=section_list, required_status=required_status,
                                           action=forward_action,
                                           form=form, version=version, message=message)
            except JSONDecodeError:
                message = "You must select at least one active subsection!"
                competence_summary = get_competence_summary_by_user(c_id, int(u_id), version)
                section_list = get_competence_by_user(c_id, int(u_id), version)

                required_status = ""
                heading = "Select Subsections"
                if forward_action == "assign":
                    required_status = None
                    heading = heading.format("assign")
                elif forward_action == "activate":
                    heading = heading.format("Activate")
                    required_status = ["Assigned"]
                elif forward_action == "evidence":
                    heading = heading.format("Assign Evidence to")
                    required_status = ["Active", "Failed", "Complete", "Sign-Off", "Not Required"]
                elif forward_action == "reassess":
                    heading = heading.format("Reassess")
                    required_status = ["Complete"]
                elif forward_action == "make_inactive":
                    heading = heading.format("Mark As Not Required")
                    required_status = ["Not Required"]

                return render_template('select_subsections.html', competence=c_id,
                                       user={'name': competence_summary.user,
                                             'id': u_id},
                                       title=competence_summary.title, validity=competence_summary.months,
                                       heading=heading,
                                       section_list=section_list, required_status=required_status,
                                       action=forward_action,
                                       form=form, version=version, message=message)

        elif forward_action == "reassess":
            comp_section_ids = []
            section_list = get_competence_by_user(c_id, int(u_id), version)
            for i in list(section_list["custom"].items())[0][1]["subsections"]:
                if i['status'] == "Complete":
                    comp_section_ids.append(str(i['id']))
            for i in list(section_list["constant"].items())[0][1]["subsections"]:
                if i['status'] == "Complete":
                    comp_section_ids.append(str(i['id']))
            print(comp_section_ids)
            """Check if user has selected every complete subsection in the competency"""
            id_check = all(id in ids for id in comp_section_ids)
            if id_check is True:
                return redirect(url_for('training.reassessment')+"?c_id="+str(c_id)+"&version="+str(version)+"&assess_id_list="+",".join(ids))
            else:
                message = "You must reassess the entire competency."
                competence_summary = get_competence_summary_by_user(c_id, int(u_id), version)
                section_list = get_competence_by_user(c_id, int(u_id), version)
                required_status = ""
                heading = "Select Subsections"
                if forward_action == "assign":
                    required_status = None
                    heading = heading.format("assign")
                elif forward_action == "activate":
                    heading = heading.format("Activate")
                    required_status = ["Assigned"]
                elif forward_action == "evidence":
                    heading = heading.format("Assign Evidence to")
                    required_status = ["Active", "Failed", "Complete", "Sign-Off", "Not Required"]
                elif forward_action == "reassess":
                    heading = heading.format("Reassess")
                    required_status = ["Complete"]
                elif forward_action == "make_inactive":
                    heading = heading.format("Mark As Not Required")
                    required_status = ["Not Required"]

                return render_template('select_subsections.html', competence=c_id,
                                       user={'name': competence_summary.user,
                                             'id': u_id},
                                       title=competence_summary.title, validity=competence_summary.months,
                                       heading=heading,
                                       section_list=section_list, required_status=required_status,
                                       action=forward_action,
                                       form=form, version=version, message=message)

        return redirect(url_for('training.view_current_competence', c_id=c_id, user=u_id,version=version))


@training.route('/retract_evidence', methods=['GET', 'POST'])
@login_required
def retract_evidence():
    """
    Method to retract evidence once sent to authoriser
    Assessment gets changed back to Active (status 1)
    Assessment evidence rel gets deleted.
    Evidence remains
    Uploads (if applicable) also remain
    :return:
    """

    user_id = current_user.database_id
    version = request.args.get('version')
    c_id = request.args.get('c_id')

    evidence_id = request.args.get('evidence_id')

    assessment_id = request.args.get('assessment_id')
    assessment = s.query(Assessments).filter(Assessments.id==assessment_id).all()
    if len(assessment) == 1 and int(assessment[0].user_id) == int(user_id) and int(assessment[0].status) == 7:
        evidence = s.query(AssessmentEvidenceRelationship).filter(AssessmentEvidenceRelationship.assessment_id==int(assessment_id)).all()
        if len(evidence)==1:
            print ("setting assessment status to 1 (active), remove trainer and signoff information")
            assessment[0].status = 1
            assessment[0].date_of_training = None
            assessment[0].trainer_id = None
            assessment[0].signoff_id = None
            s.commit()
        elif len(evidence)>1:
            ### assessment goes back to most recent evidence status
            print ("more evidence - deciding status")
            dates={}
            for i in evidence:
                if int(i.evidence_id) != int(evidence_id):
                    evidence_record = s.query(Evidence).filter(Evidence.id == i.evidence_id).first()
                    if evidence_record.is_correct == 1:
                        dates[evidence_record.date_completed] = "correct"
                    elif evidence_record.is_correct == 0:
                        dates[evidence_record.date_completed] = "incorrect"
                    elif evidence_record.is_correct is None:
                        dates[evidence_record.date_completed] = "signoff"

            ### get most recent date - this determines the status of the assessment
            most_recent = max(dates.keys())

            if dates[most_recent] == "correct":
                assessment[0].status = 3
                assessment[0].date_of_training = most_recent.strftime("%Y-%m-%d")
            elif dates[most_recent] == "incorrect":
                assessment[0].status = 5
                assessment[0].date_of_training = most_recent.strftime("%Y-%m-%d")
            elif dates[most_recent] == "signoff":
                assessment[0].status = 7
                assessment[0].date_of_training = most_recent.strftime("%Y-%m-%d")

            s.commit()

    evidence_assess_rel = s.query(AssessmentEvidenceRelationship).filter(AssessmentEvidenceRelationship.evidence_id==int(evidence_id)).filter(AssessmentEvidenceRelationship.assessment_id==int(assessment_id)).all()
    if len(evidence_assess_rel) == 1:
        s.delete(evidence_assess_rel[0])
        s.commit()

    ###check if evidence is linked to other assessments, if not, delete evidence and any associated uploads
    evidence_assess_rel_other = s.query(AssessmentEvidenceRelationship).filter(AssessmentEvidenceRelationship.evidence_id==int(evidence_id)).all()
    if len(evidence_assess_rel_other) == 0:
        uploads = s.query(Uploads).filter(Uploads.evidence_id == int(evidence_id)).all()
        for i in uploads:
            s.delete(i)
            s.commit()
        evidence_record = s.query(Evidence).filter(Evidence.id == int(evidence_id)).first()
        s.delete(evidence_record)
        s.commit()

    return redirect(url_for('training.view_current_competence', version=version, c_id=c_id))



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


@training.route('/bulk_distribute', methods=['GET', 'POST'])
@login_required
def bulk_distribute():
    if request.method == "GET":
        # get ID for user
        form = UserAssignForm()
        users_alias = aliased(Users)

        # get info for competence (assessments table)
        competence_result = s.query(Assessments). \
            outerjoin(Users, Assessments.signoff_id == Users.id). \
            outerjoin(users_alias, Assessments.trainer_id == Users.id). \
            outerjoin(Subsection). \
            outerjoin(Section). \
            outerjoin(Competence, Subsection.c_id == Competence.id). \
            outerjoin(AssessmentStatusRef, Assessments.status == AssessmentStatusRef.id). \
            outerjoin(EvidenceTypeRef). \
            filter(and_(Assessments.assign_id == current_user.database_id, Assessments.trainer_id == None,
                        Assessments.signoff_id == None)).all()
        # values(Assessments.id, Section.name, Section.constant, Subsection.id,
        #        Subsection.name.label('area_of_competence'), Subsection.comments.label('notes'), EvidenceTypeRef.type,
        #        AssessmentStatusRef.status, (Users.first_name + ' ' + Users.last_name).label('assessor'),
        #        (users_alias.first_name + ' ' + users_alias.last_name).label('trainer'), Assessments.date_of_training,
        #        Assessments.date_completed, Assessments.date_expiry, Assessments.comments.label('training_comments'))


        return render_template('bulk_distribute.html', competence_result=competence_result, form=form)

    elif request.method == "POST":
        for i in zip(request.form.getlist('assid'), request.form.getlist('trainer'), request.form.getlist('assessor')):
            print (i)

@training.route('/four_year_activate/<c_id>', methods=['GET', 'POST'])
@login_required
def four_year_activate(c_id = None):
    """
    set all assessments in current competency to obsolete and assign the latest version of
    the competency to the user - probably need to check if competence exists anymore?
    :return:
    """
    #TODO is THIS implemented anywhere?
    #get assessment ids for user and competence

    assessments = s.query(Assessments).\
        join(Subsection).\
        join(Competence).\
        join(AssessmentStatusRef).\
        filter(or_(AssessmentStatusRef.status == "Complete",AssessmentStatusRef.status == "Four Year Due")).\
        filter(Competence.id==c_id).\
        filter(Assessments.user_id == current_user.database_id).all()

    # set current assessments in this competency to obsolete
    status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Obsolete").first().id
    data = { 'status': status_id }
    for assessment in assessments:
        s.query(Assessments).filter(Assessments.id == assessment.id).update(data)
    s.commit()

    # assign user new assessments in the latest version of the competency and set them to active
    from app.mod_competence.views import assign_competence_to_user
    due_date = datetime.date.today() + relativedelta(months=1)
    assessment_ids = assign_competence_to_user(current_user.database_id,c_id,due_date.strftime("%d/%m/%Y"))

    data = {'is_reassessment':True}

    for i in assessment_ids:
        s.query(Assessments).filter(Assessments.id == i).update(data)
    s.commit()


@training.route('/test', methods=['GET', 'POST'])
def test():
    #TODO is this implemented anywhere?
    four_years_ago = datetime.date.today() - relativedelta(months=48)

    assessments = s.query(Assessments).join(AssessmentStatusRef).filter(
        AssessmentStatusRef.status == "Complete").filter(Assessments.date_completed <= four_years_ago)


    done = []
    for assessment in assessments:

        #update assessment status to indicate that 4 year is now due (maybe set them all?)
        status = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Four Year Due").first().id
        data = { "status": status }
        s.query(Assessments).filter(Assessments.id == assessment.id).update(data)

        #only send email once for that competency
        if str(assessment.user_id) + ":" + str(assessment.ss_id_rel.c_id) not in done:

            lines = [assessment.ss_id_rel.c_id_rel.competence_detail[0].title + " is due for a four year reassessment."]
            lines.append("You originally completed this competency on "+str(assessment.date_completed))
            lines.append("Please arrange a suitable time with your trainer to reassess you competence fully.")

            print (send_mail(assessment.user_id ,"Four Year Competency Reassessment Required: "+ assessment.ss_id_rel.c_id_rel.competence_detail[0].title,"<br><br>".join(lines)))

        done.append(str(assessment.user_id) + ":" + str(assessment.ss_id_rel.c_id))

    s.commit()

def fill_time_series(dictionary):
    ##fils times series dictionary with zeroes on days that nothing is done
    earlier_date=sorted(dictionary)[0]
    today = datetime.date.today()
    date = earlier_date
    while date != today:
        date+=datetime.timedelta(days=1)
        if date not in dictionary:
            dictionary[date] = 0

    return dictionary


@training.route('/user_report/<id>', methods=['GET'])
def user_report(id=None):
    user = s.query(Users).filter(Users.id==id).first()

    ###get ongoing competencies and split into overdue and in-date

    ### get all assessments that are assigned, abandoned or waiting for sign-off
    assigned = s.query(Assessments)\
        .join(Subsection)\
        .join(Competence)\
        .join(CompetenceDetails)\
        .join(AssessmentStatusRef)\
        .filter(Assessments.user_id == id)\
        .group_by(Competence.id) \
        .filter(CompetenceDetails.intro == Competence.current_version) \
        .filter(or_(AssessmentStatusRef.status == "Assigned", AssessmentStatusRef.status == "Active", AssessmentStatusRef.status == "Sign-Off"))\
        .all()

    ### get all assessments that are abandoned
    abandoned_query = s.query(Assessments)\
        .join(Subsection)\
        .join(Competence)\
        .join(CompetenceDetails)\
        .join(AssessmentStatusRef)\
        .filter(Assessments.user_id == id)\
        .group_by(Competence.id) \
        .filter(CompetenceDetails.intro == Competence.current_version) \
        .filter(AssessmentStatusRef.status == "Abandoned")\
        .all()

    completed=[]
    ongoing=[]
    overdue=[]
    expired=[]
    abandoned=[]
    expiring_within_month=[]
    today = datetime.date.today()

    for j in assigned:
        ongoing_assessment_summary = get_competence_summary_by_user(c_id=j.ss_id_rel.c_id,u_id=id,version=j.version)
        if ongoing_assessment_summary.due_date <= today:
            overdue.append(ongoing_assessment_summary)
        else:
            ongoing.append(ongoing_assessment_summary)

    for i in abandoned_query:
        abandoned_assessment_summary = get_competence_summary_by_user(c_id=i.ss_id_rel.c_id,u_id=id,version=i.version)
        abandoned.append(abandoned_assessment_summary)

    ### get complete competencies and split into expiring, expired, and in-date
    ### NC Oct 21 - edited to add competencies marked as not required
    complete = s.query(Assessments) \
        .join(Subsection)\
        .join(Competence)\
        .join(CompetenceDetails)\
        .join(AssessmentStatusRef)\
        .filter(Assessments.user_id == id) \
        .group_by(Competence.id) \
        .filter(CompetenceDetails.intro == Competence.current_version) \
        .filter(AssessmentStatusRef.status.in_(["Complete","Four Year Due","Not Required"])) \
        .all()

    for i in complete:
        complete_assessment_summary = get_competence_summary_by_user(c_id=i.ss_id_rel.c_id, u_id=id, version=i.version)
        if complete_assessment_summary.completed != None:
            if complete_assessment_summary.expiry <= today:
                expired.append(complete_assessment_summary)
            elif abs((complete_assessment_summary.expiry - today).days) <= 30:
                expiring_within_month.append(complete_assessment_summary)
            else:
                completed.append(complete_assessment_summary)

    ########################
    ###   Contribution   ###
    ########################

    # get assessments signed off  and trained by user and date of sign-off

    signed_off_query = s.query(Assessments).filter(Assessments.signoff_id == id).filter(Assessments.user_id != id).values(Assessments.date_completed)
    signed_off_dates_dict={}
    trained_dates_dict={}
    signed_off_dates=[]
    trained_dates=[]
    signed_off_counts=[]
    trained_counts=[]
    for i in signed_off_query:
        if i.date_completed is not None:
            if i.date_completed not in signed_off_dates_dict:
                signed_off_dates_dict[i.date_completed] = 1
            else:
                signed_off_dates_dict[i.date_completed] +=1

    if len(signed_off_dates_dict.keys()) > 0:
        signed_off_dates_dict_filled = fill_time_series(signed_off_dates_dict)

        for date in sorted(signed_off_dates_dict_filled):
            signed_off_dates.append(date)
            signed_off_counts.append(signed_off_dates_dict_filled[date])


    trained_query = s.query(Assessments).filter(Assessments.trainer_id == id).filter(Assessments.user_id != id).values(Assessments.date_of_training)
    for i in trained_query:
        if i.date_of_training is not None:
            if i.date_of_training not in trained_dates_dict:
                trained_dates_dict[i.date_of_training] = 1
            else:
                trained_dates_dict[i.date_of_training] +=1

    if len(trained_dates_dict.keys()) > 0:
        trained_dates_dict_filled = fill_time_series(trained_dates_dict)

        for date in sorted(trained_dates_dict_filled):
            trained_dates.append(date)
            trained_counts.append(trained_dates_dict_filled[date])

    if len(signed_off_dates) > 0 and len(trained_dates) == 0:
        trained_dates = signed_off_dates
        trained_counts = [0]* len(signed_off_dates)
    elif len(trained_dates) > 0 and len(signed_off_dates) == 0:
        signed_off_dates = trained_dates
        signed_off_counts = [0]* len(trained_dates)

    signed_off_df = {'Date': signed_off_dates, 'count': signed_off_counts}
    trained_df = {'Date': trained_dates, 'count': trained_counts}

    data = [go.Scatter(x=signed_off_df['Date'], y=signed_off_df['count'], name='Signed off'),
                     go.Scatter(x=trained_df['Date'], y=trained_df['count'], name='Trained')]
    layout = go.Layout(margin=go.layout.Margin(t=50, b=50), title='Training',height=300)
    fig = go.Figure(data=data,layout=layout)
    training_plot = plot(fig, output_type="div")

    #get documents written and authorised by user
    creator_dates_dict={}
    approver_dates_dict={}
    creater_dates = []
    creater_counts=[]
    approver_dates=[]
    approver_counts=[]

    creator_query = s.query(CompetenceDetails).filter(CompetenceDetails.creator_id == id).values(CompetenceDetails.date_created)
    #DO NOT REMOVE THIS PRINT STATEMENT without it the page won't load
    #TODO work out how to fix this properly
    for creator in creator_query:
        print(creator)
    approver_query = s.query(CompetenceDetails).filter(CompetenceDetails.approve_id == id).values(CompetenceDetails.date_of_approval)

    for i in creator_query:
        if i.date_created is not None:
            if i.date_created not in creator_dates_dict:
                creator_dates_dict[i.date_created] = 1
            else:
                creator_dates_dict[i.date_created] +=1

    for i in approver_query:
        if i.date_of_approval is not None:
            if i.date_of_approval not in approver_dates_dict:
                approver_dates_dict[i.date_of_approval] = 1
            else:
                approver_dates_dict[i.date_of_approval] += 1

    if len(approver_dates_dict.keys()) > 0:
        approver_dates_dict_filled = fill_time_series(approver_dates_dict)
        for date in sorted(approver_dates_dict_filled):
            approver_dates.append(date)
            approver_counts.append(approver_dates_dict_filled[date])

    if len(creator_dates_dict.keys()) > 0:
        creater_dates_dict_filled = fill_time_series(creator_dates_dict)
        for date in sorted(creater_dates_dict_filled):
            creater_dates.append(date)
            creater_counts.append(creater_dates_dict_filled[date])

    if len(approver_dates) > 0 and len(creater_dates) == 0:
        creater_dates = approver_dates
        creater_counts = [0]* len(approver_dates)
    elif len(creater_dates) > 0 and len(approver_dates) == 0:
        approver_dates = creater_dates
        approver_counts = [0]* len(creater_dates)

    approver_df = {'Date': approver_dates, 'count': approver_counts}
    creater_df = {'Date': creater_dates, 'count': creater_counts}

    doc_data = [go.Scatter(x=creater_df['Date'], y=creater_df['count'], name='Created'),
                     go.Scatter(x=approver_df['Date'], y=approver_df['count'], name='Approved')]
    doc_layout = go.Layout(margin=go.layout.Margin(t=50), title='Documents',height=300)
    doc_fig = go.Figure(data=doc_data,layout=doc_layout)
    document_plot = plot(doc_fig, output_type="div")

    ################
    ### Accuracy ###
    ################
    correct=0
    incorrect=0
    accuracy_query = s.query(Evidence) \
        .join(AssessmentEvidenceRelationship) \
        .join(Assessments) \
        .filter(Assessments.user_id == id) \
        .all()

    for i in accuracy_query:
        if i.is_correct is True:
            correct+=1
        else:
            incorrect+=1

    if correct== 0 and incorrect==0:
        correct_percent=0
        incorrect_percent=0
    else:
        correct_percent = float(correct)*100 / float(correct+incorrect)
        incorrect_percent = float(incorrect) * 100 / float(correct + incorrect)

    correct_data = go.Bar(x=[correct_percent],y=['Evidence '], orientation='h', name="% Approved",width=[0.4])
    incorrect_data = go.Bar(x=[incorrect_percent], y=['Evidence '], orientation='h', name="% Rejected", width=[0.4])
    data=[correct_data, incorrect_data]
    layout=go.Layout(margin=go.layout.Margin(t=50),barmode='stack', height=250, xaxis=dict(title='Percentage'))
    accuracy_fig=go.Figure(data=data, layout=layout)
    accuracy_plot=plot(accuracy_fig, output_type="div")

    ##########################
    ### Time to Completion ###
    ##########################

    assigned_to_activation_list = []
    activated_to_completion_list = []
    assigned_to_completion_list = []
    days_over_target_list = []
    overdue_assessments = 0
    indate_assessments = 0

    all_assessments = s.query(Assessments) \
        .join(Subsection) \
        .join(Competence) \
        .join(CompetenceDetails) \
        .join(AssessmentStatusRef) \
        .filter(Assessments.user_id == id) \
        .all()

    for i in all_assessments:
        if i.date_activated is not None and i.date_assigned is not None:
            days_assigned_to_activation = abs((i.date_activated - i.date_assigned).days)
            assigned_to_activation_list.append(days_assigned_to_activation)
        if i.date_activated is not None and i.date_completed is not None and float(i.signoff_id) != float(id):
            days_activated_to_completion = abs((i.date_completed - i.date_activated).days)
            activated_to_completion_list.append(days_activated_to_completion)
        if i.date_assigned is not None and i.date_completed is not None and float(i.signoff_id) != float(id):
            days_assigned_to_completion = abs((i.date_completed - i.date_assigned).days)
            assigned_to_completion_list.append(days_assigned_to_completion)

        ### do stuff for due dates section here, rather than looping again later on
        if i.date_completed is not None and i.due_date is not None:
            if i.date_completed > i.due_date:
                overdue_assessments+=1
            else:
                indate_assessments+=1

            days_over_target = int((i.date_completed - i.due_date).days)
            days_over_target_list.append(days_over_target)

    violin_data = [
        {
            "type": 'violin',
            "y": assigned_to_activation_list,
            "name": "Assigned to Activated",
            "jitter":0.3,
            "points": "all",
            "pointpos":0

        },
        {
            "type": 'violin',
            "y": activated_to_completion_list,
            "name": "Activated to Completed",
            "jitter":0.3,
            "points": "all",
            "pointpos": 0
        },
        {
            "type": 'violin',
            "y": assigned_to_completion_list,
            "name": "Assigned to Completed",
            "jitter":0.3,
            "points": "all",
            "pointpos": 0
        }
    ]
    layout = go.Layout(margin=go.layout.Margin(t=50), height=500, yaxis=dict(title='Days'))
    violin_fig = go.Figure(data=violin_data, layout=layout)
    violin_plot = plot(violin_fig, output_type="div")

    #################
    ### Due Dates ###
    #################

    if overdue_assessments == 0 and indate_assessments == 0:
        overdue_percentage = 0
        indate_percentage = 0
    else:
        overdue_percentage = float(overdue_assessments)*100 / float(overdue_assessments + indate_assessments)
        indate_percentage = float(indate_assessments)*100 / float(overdue_assessments + indate_assessments)

    overdue_data = go.Bar(x=[overdue_percentage], y=['Completed Assessments '], orientation='h', name="% Overdue", width=[0.4])
    indate_data = go.Bar(x=[indate_percentage], y=['Completed Assessments '], orientation='h', name="% Indate", width=[0.4])
    data = [overdue_data,indate_data]
    layout = go.Layout(margin=go.layout.Margin(t=50,l=160), barmode='stack', height=250,xaxis=dict(title='Percentage'))
    target_fig = go.Figure(data=data, layout=layout)
    target_plot = plot(target_fig, output_type="div")

    target_violin_data = [
        {
            "type": 'violin',
            "x": days_over_target_list,
            "name": "Complete Assessments",
            "jitter": 0.5,
            "points": "all",
            "pointpos": 0
        }
    ]
    layout = go.Layout(margin=go.layout.Margin(t=10,l=150,r=120), height=250, xaxis=dict(title='Days over / under target due date'))
    target_violin_fig = go.Figure(data=target_violin_data, layout=layout)
    target_violin_plot = plot(target_violin_fig, output_type="div")

    return render_template("user_report.html",user=user, overdue=overdue, ongoing=ongoing, abandoned=abandoned, completed=completed, expired=expired,
                           expiring=expiring_within_month, signed_off_plot=Markup(training_plot), document_plot=Markup(document_plot),
                           accuracy_plot=Markup(accuracy_plot), violin_plot=Markup(violin_plot), target_plot=Markup(target_plot),
                           target_violin_plot=Markup(target_violin_plot))

