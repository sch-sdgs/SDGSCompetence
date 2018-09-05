from flask import Flask, render_template, redirect, request, url_for, session, current_app, Blueprint, \
    send_from_directory, jsonify
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from app.competence import s,send_mail
from app.models import *
from sqlalchemy.sql.expression import func, and_, or_, case, exists, update, asc
from sqlalchemy.orm import aliased
import datetime
from dateutil.relativedelta import relativedelta
import os
from forms import *
import uuid
import json
from collections import OrderedDict
from app.competence import config


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
        return html

    return dict(make_status_label=make_status_label)


###########
# Queries #
###########

def get_ss_id_from_assessment(assess_id_list):
    assess_id_list = [ int(x) for x in assess_id_list ]
    ss_ids_res = s.query(Assessments).filter(Assessments.id.in_(assess_id_list)).values(Assessments.ss_id)
    ss_ids = []

    for ss_id in ss_ids_res:
        ss_ids.append(ss_id.ss_id)

    return ss_ids


def get_competent_users(ss_id_list):
    # todo: add competence author to this list

    print "HELLO THERE"
    print ss_id_list

    users = s.query(Users). \
        join(Assessments, Assessments.user_id == Users.id). \
        join(AssessmentStatusRef). \
        filter(AssessmentStatusRef.status == "Complete",
               Assessments.date_expiry > datetime.date.today(),
               Assessments.ss_id.in_(ss_id_list)). \
        group_by(Users.id).having(func.count(Assessments.ss_id.in_(ss_id_list)) == len(ss_id_list)). \
        values(Users.id, (Users.first_name + ' ' + Users.last_name).label('name'))

    return users


def get_competence_by_user(c_id, u_id,version):
    """
    Method to get information for competence for a given user

    :param c_id: ID for competence
    :param u_id: ID of user
    :return:
    """
    # get ID for user

    #users_alias = aliased(Users)

    # get info for competence (assessments table)

    competence_result = s.query(Assessments). \
        join(Subsection). \
        join(Section). \
        join(SectionSortOrder). \
        join(Competence). \
        join(CompetenceDetails, and_(Competence.id==CompetenceDetails.c_id,CompetenceDetails.intro==version)). \
        join(AssessmentStatusRef). \
        join(EvidenceTypeRef). \
        filter(AssessmentStatusRef.status != "Obsolete" ). \
        filter(and_(Assessments.user_id == u_id, Competence.id == c_id, Assessments.version==version)). \
        order_by(asc(Section.name)).order_by(asc(Subsection.sort_order)).order_by(asc(SectionSortOrder.sort_order)).\
        values(Assessments.id.label('ass_id'), Section.name, Section.constant, Subsection.id, Assessments.trainer_id, Assessments.signoff_id,
               Subsection.name.label('area_of_competence'), Subsection.comments.label('notes'), EvidenceTypeRef.type,
               AssessmentStatusRef.status, Assessments.date_of_training,
               Assessments.date_completed, Assessments.date_expiry, Assessments.comments.label('training_comments'),Assessments.version,SectionSortOrder.sort_order)

    print "COUNT"
    print competence_result

    result = {'constant': OrderedDict(), 'custom': OrderedDict()}

    for_order = s.query(SectionSortOrder).filter(SectionSortOrder.c_id == c_id).order_by(
        asc(SectionSortOrder.sort_order)).all()
    for x in for_order:
        check = s.query(Subsection).filter(Subsection.s_id == x.section_id).filter(
            and_(Subsection.intro <= version, or_(Subsection.last > version, Subsection.last == None))).count()

        if check > 0:
            if x.section_id_rel.constant == 1:
                result["constant"][x.section_id_rel.name] = OrderedDict()
                result["constant"][x.section_id_rel.name] = {'complete': 0, 'total': 0, 'subsections': []}
            else:
                result["custom"][x.section_id_rel.name] = OrderedDict()
                result["custom"][x.section_id_rel.name] = {'complete': 0, 'total': 0, 'subsections': []}

    print json.dumps(result, indent=4)

    for c in competence_result:
        print "hello MEMEMME"
        print c.name
        print c.ass_id
        evidence = s.query(AssessmentEvidenceRelationship).filter(
            AssessmentEvidenceRelationship.assessment_id == c.ass_id).all()
        print evidence
        if c.constant:
            d = 'constant'
        else:
            d = 'custom'

        #todo repleace this with relationship in assessments - back_populates?
        trainer = "-"
        if c.trainer_id is not None:
            q = s.query(Users).filter(Users.id==c.trainer_id).first()
            trainer = q.first_name + " " + q.last_name

        assessor = "-"
        if c.signoff_id is not None:
            q = s.query(Users).filter(Users.id == c.signoff_id).first()
            assessor = q.first_name + " " + q.last_name


        if c.name not in result[d].keys():
            result[d][c.name] = {'complete': 0, 'total': 0, 'subsections': []}

        #Feb 2018 - I have changed this here to be the assessment id - instead of the c.id
        subsection = {'id': c.ass_id,
                      'name': c.area_of_competence,
                      'status': c.status,
                      'evidence_type': c.type,
                      'assessor': assessor,
                      'date_of_completion': filter_for_none(c.date_completed),
                      'notes': filter_for_none(c.notes),
                      'training_comments': filter_for_none(c.training_comments),
                      'trainer': trainer,
                      'date_of_training': filter_for_none(c.date_of_training),
                      'evidence': filter_for_none(evidence)}
        if c.date_completed:
            result[d][c.name]['complete'] += 1
        result[d][c.name]['total'] += 1
        subsection_list = result[d][c.name]['subsections']
        subsection_list.append(subsection)
        result[d][c.name]['subsections'] = subsection_list

    return result


def get_competence_summary_by_user(c_id, u_id,version):
    """

    :param c_id:
    :param u_id:
    :return:
    """
    print "YOYOYOY"
    competence_result = s.query(Assessments).outerjoin(Users, Users.id == Assessments.user_id).outerjoin(Subsection). \
        outerjoin(Section).outerjoin(Competence, Subsection.c_id == Competence.id). \
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
               case([
                   (s.query(Assessments). \
                    outerjoin(Subsection, Subsection.id == Assessments.ss_id).\
                    filter(and_(Assessments.version==version,Assessments.user_id == u_id, Subsection.c_id == c_id,
                                Assessments.date_completed == None)).exists(),
                    None)],
                   else_=func.max(Assessments.date_completed)).label('completed'))
               # case([
               #     (s.query(Assessments). \
               #      outerjoin(Subsection, Subsection.id == Assessments.ss_id).\
               #      filter(and_(Assessments.version==version,Assessments.user_id == u_id, Subsection.c_id == c_id,
               #                  Assessments.date_expiry == None)).exists(),
               #      None)],
               #     else_=func.min(Assessments.date_expiry)).label('expiry'))

    for comp in competence_result:
        return comp


def activate_assessments(ids, u_id,version):
    """


    :return:
    """
    print "here"
    if ids[0] != "":
        ids = [int(x) for x in ids]
    else:
        return False


    activated = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Active").first().id
    assigned = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Assigned").first().id

    print('activated = ' + str(activated))
    print('assigned = ' + str(assigned))
    print('query')
    print(s.query(Assessments).filter(
        and_(Assessments.user_id == u_id, Assessments.status == assigned, Assessments.id.in_(ids))))
    print(s.query(Assessments).filter(
        and_(Assessments.user_id == u_id, Assessments.status == assigned, Assessments.id.in_(ids))))
    statement = s.query(Assessments). \
        filter(and_(Assessments.version==version,Assessments.user_id == u_id, Assessments.status == assigned, Assessments.id.in_(ids))). \
        update({Assessments.status: activated, Assessments.date_activated: datetime.date.today()},
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
        print c_id

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

        competent_users = get_competent_users(ss_id_list)

        choices = []
        for user in competent_users:
            if user.id != current_user.database_id:
                choices.append((user.id, user.name))
        #todo append competence author

        form.signoff_id.choices = choices
        return render_template('reassessment.html', data=data, c_id=c_id, user_id=u_id,
                               competence_name=competence_summary.title, form=form,
                               assess_id_list=','.join(assess_id_list),version=version)

    elif request.method == 'POST':
        print "now posting"
        questions = s.query(QuestionsRef).filter(QuestionsRef.active == True).all()

        signoff_id = request.form["signoff_id"]

        assess_id_list = request.args.get('assess_id_list').split(',')

        reassessment = Reassessments(signoff_id)
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

    reassessment = s.query(Reassessments).join(AssessReassessRel).filter(Reassessments.id==reassess_id).group_by(AssessReassessRel.reassess_id).first()

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
        print "HERE"
        print competence_summary.activated
        reassessments = s.query(Reassessments).join(AssessReassessRel).join(Assessments).join(AssessmentStatusRef).join(Subsection).join(Competence).filter(AssessmentStatusRef.status != "Obsolete").filter(Assessments.user_id==u_id).filter(Competence.id==c_id).filter(Assessments.version==version).all()
        print "DETAILLLS"
        detail_id = s.query(CompetenceDetails).join(Competence).filter(CompetenceDetails.c_id == c_id).filter(and_(CompetenceDetails.intro <= version,
                                                                 or_(
                                                                     CompetenceDetails.last >= version,
                                                                     CompetenceDetails.last == None))).first().id

        videos = s.query(Videos).filter(Videos.c_id==detail_id).all()
        four_year_check = s.query(Assessments).join(Subsection).join(Competence).join(AssessmentStatusRef).filter(Assessments.user_id==u_id).filter(AssessmentStatusRef.status=="Four Year Due").filter(Competence.id==c_id).count()
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
                               version=competence_summary.version,
                               reassessments=reassessments,videos=videos,four_year_check=four_year_check)


@training.route('/upload')
@login_required
def upload_evidence(c_id=None, s_ids=None,version=None):
    """
    Method to

    :return:
    """

    ass_ids = json.loads(request.form["ids"])
    form = UploadEvidence()

    ss_id_list = get_ss_id_from_assessment(ass_ids)

    competent_users = get_competent_users(ss_id_list)

    #sub_section_name = ass.ss_id_rel.name

    choices = []
    for user in competent_users:
        choices.append((user.id, user.name))

    # append competence author
    # author = s.query(Users).filter(Users.id == ass.ss_id_rel.c_id_rel.competence_detail[0].creator_id).first()
    # choices.append((author.id, author.first_name + " " + author.last_name))

    form.trainer.choices = choices
    form.assessor.choices = choices
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
            print "HERE"
            for j in i.assessments_rel:
                current_version = j.assess_rel.ss_id_rel.c_id_rel.current_version
                print "CURRENT"
                print current_version
                for detail in j.assess_rel.ss_id_rel.c_id_rel.competence_detail:
                    if detail.intro <= current_version:
                        print "CURRENT EXPIRY"
                        print i.date_completed
                        new_expiry = i.date_completed + relativedelta(months=detail.validity_rel.months)
                        print "NEW_EXPIRY"
                        print new_expiry


                print j.assess_id

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
    print uploads
    return send_from_directory(directory=uploads, filename=filename, as_attachment=True, attachment_filename=alias)

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
            print assess_id
            ss_id_list = get_ss_id_from_assessment([assess_id])
            print ss_id_list
            competent_users = get_competent_users(ss_id_list)

            sub_section_name = ass.ss_id_rel.name

            choices = []
            for user in competent_users:
                choices.append((user.id, user.name))

            #append competence author
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
        print data
        s.query(Assessments).filter(Assessments.id==assess_id).update(data)
        s.commit()

@training.route('/self_complete/<int:assess_id>', methods=['GET', 'POST'])
@login_required
def self_complete(assess_id):
    print assess_id
    c_id = request.args.get('c_id')
    version = request.args.get('version')
    status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Complete").first().id

    query = s.query(Assessments).filter(Assessments.id == assess_id).first()

    for detail in query.ss_id_rel.c_id_rel.competence_detail:
        if detail.intro <= query.version:
            print "YOY"
            print detail
            months_valid = detail.validity_rel.months

    data = {'trainer_id': current_user.database_id,
            'date_of_training': datetime.date.today(),
            'date_completed': datetime.date.today(),
            'date_expiry': datetime.date.today() + relativedelta(months=months_valid),
            'signoff_id': current_user.database_id,
            'status': status_id,
            }
    print "hello"
    print data
    s.query(Assessments).filter(Assessments.id == assess_id).update(data)
    s.commit()
    return redirect(url_for('training.view_current_competence')+"?c_id="+str(c_id)+"&version="+str(version))

@training.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():

    c_id = request.args["c_id"]
    #find assessments records for this competence for current user
    assessments = s.query(Assessments).join(Subsection).filter(and_(Subsection.c_id == c_id,Assessments.user_id==current_user.database_id)).all()

    for assessment in assessments:
        evidence_rels = s.query(AssessmentEvidenceRelationship).filter(AssessmentEvidenceRelationship.assessment_id == assessment.id).all()
        print evidence_rels
        if len(evidence_rels) > 0:
            for evidence_rel in evidence_rels:
                print evidence_rel.evidence_id
                #remove upload
                print "removing upload"
                files = s.query(Uploads).filter_by(evidence_id = evidence_rel.evidence_id).all()
                if len(files) > 0:
                    for file in files:
                        try:
                            os.remove(config.UPLOADED_FILES_DEST+"/"+file.uuid)
                            print "file removed"
                        except OSError:
                            print "couldn't remove file from filesystem"
                print "deleting upload from db"
                s.query(Uploads).filter_by(evidence_id = evidence_rel.evidence_id).delete()
                s.commit()

                #remove_evidence_rel
                print "removing evidence rel"
                s.query(AssessmentEvidenceRelationship).filter_by(id=evidence_rel.id).delete()
                s.commit()
                # remove evidence
                print "removing eveidne record in db"
                s.query(Evidence).filter_by(id=evidence_rel.evidence_id).delete()
                s.commit()

        reassessments = s.query(AssessReassessRel).filter_by(assess_id=assessment.id).all()
        if len(reassessments) > 0:
            for reassessment in reassessments:
                print "removing reassessments"
                s.query(Reassessments).filter_by(id=reassessment.reassess_id).delete()
                s.commit()

        print "removing reassess rel"
        s.query(AssessReassessRel).filter_by(assess_id=assessment.id).delete()
        s.commit()

        print "removing reassessment"
        s.query(Assessments).filter_by(id=assessment.id).delete()
        s.commit()

    return json.dumps({'success': True})



@training.route('/abandon', methods=['GET', 'POST'])
@login_required
def abandon():
    c_id = request.args["c_id"]
    print "hello"
    print c_id
    version = request.args["version"]
    abandon_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status=="Abandoned").first().id
    data = {'status':abandon_id}
    assessments = s.query(Assessments).join(Subsection).filter(and_(Subsection.c_id == c_id, Assessments.version == version)).all()
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




    if action == "accept":
        data = {
            'is_correct': 1,
            'comments': request.form["comments"],
        }
        s.query(Evidence).filter(Evidence.id == evidence_id).update(data)
        status = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Complete").first().id
        date = datetime.date.today()
    elif action == "reject":
        data = {
            'is_correct': 0,
            'comments': request.form["comments"],
        }
        s.query(Evidence).filter(Evidence.id == evidence_id).update(data)
        status = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Failed").first().id
        date = None

    assessments_to_update = s.query(AssessmentEvidenceRelationship).filter(AssessmentEvidenceRelationship.evidence_id == evidence_id).all()



    for assessment in assessments_to_update:
        print "HERE"
        print status
        print assessment.assessment_id


        query = s.query(Assessments).filter(Assessments.id == assessment.assessment_id).first()

        for detail in query.ss_id_rel.c_id_rel.competence_detail:
            if detail.intro <= query.version:
                print "YOY"
                print detail
                months_valid = detail.validity_rel.months

        data = {
            'date_completed': date,
            'status': status,
            'date_expiry': datetime.datetime.now() + relativedelta(months=months_valid)
        }

        s.query(Assessments).filter(Assessments.id ==assessment.assessment_id).update(data)
        s.commit()


    send_mail(query.user_id, "Evidence Reviewed",
              "Your evidence was reviewed by <b>" + current_user.full_name + "</b>")

    # else:
    #     print "NOT AUTHORISED"

    return redirect(url_for('index'))

@training.route('/process_evidence', methods=['GET', 'POST'])
@login_required
def process_evidence():

    s_ids = request.args.get('s_ids').split(",")
    c_id = request.args.get('c_id')
    version = request.args.get('version')
    status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Sign-Off").first().id
    for i in request.form:
        print i

    evidence_type = s.query(EvidenceTypeRef).filter(EvidenceTypeRef.id == int(request.form['evidence_type'])).first().type

    print evidence_type



    if evidence_type == "Case":
        evidence = request.form.getlist('case')
        result = request.form.getlist('result')
        for i in zip(evidence,result):
            print i
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
            print "Observation"
            print "HERE ME"
            print request.form['evidence_observation']
            evidence = request.form['evidence_observation']
            result = None

        e = Evidence(is_correct=None, signoff_id=request.form['assessor'], date=datetime.date.today(),
                     evidence=evidence, result=result,
                     comments=None, evidence_type_id=request.form["evidence_type"])
        s.add(e)
        s.commit()
        for assess_id in s_ids:
            er = AssessmentEvidenceRelationship(assess_id, e.id)
            s.add(er)



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

        # generate uuid incase someone uploads file of same name and it's actually different - store real name in db
        upload_filename = str(uuid.uuid4())

        for f in uploaded_files:
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], upload_filename))
            u = Uploads(upload_filename, f.filename, current_user.database_id, e.id)
            s.add(u)
        s.commit()


    send_mail(request.form['trainer'], "Evidence awaiting your review",
              "You have evidence uploaded by <b>" + current_user.full_name + "</b> awaiting your review.")

    return redirect(url_for('training.view_current_competence')+"?version="+str(version)+"&c_id="+str(c_id))


# @training.route('/uploader', methods=['GET', 'POST'])
# @login_required
# def file_uploader():
#     if request.method == 'POST':
#         f = request.files['upload']
#         f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
#         print(f.filename)
#         return 'file uploaded successfully'

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
    version = request.args.get('version')
    u_id = current_user.database_id

    forward_action = request.args.get('action')
    print(forward_action)

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
            required_status = ["Assigned"]
        elif forward_action == "evidence":
            heading = heading.format("Assign Evidence to")
            required_status = ["Active","Failed","Complete","Sign-Off"]
        elif forward_action == "reassess":
            heading = heading.format("Reassess")
            required_status = ["Complete"]

        return render_template('select_subsections.html', competence=c_id, user={'name': competence_summary.user,
                                                                                 'id': u_id},
                               title=competence_summary.title, validity=competence_summary.months, heading=heading,
                               section_list=section_list, required_status=required_status, action=forward_action,
                               form=form,version=version)
    else:
        print request.form["ids"]
        ids = form.ids.data.replace('"', '').replace('[', '').replace(']', '').split(',')
        if forward_action == "assign":
            pass
        elif forward_action == "activate":
            print "THIS IS ME"
            print ids
            result = activate_assessments(ids, u_id,version)
            if result == False:
                return redirect(url_for('training.view_current_competence', c_id=c_id, user=u_id, version=version))

        elif forward_action == "evidence":
            print "HELLO"
            print ids
            return upload_evidence(c_id, ids,version)
        elif forward_action == "reassess":
            return redirect(url_for('training.reassessment')+"?c_id="+str(c_id)+"&version="+str(version)+"&assess_id_list="+",".join(ids))

        return redirect(url_for('training.view_current_competence', c_id=c_id, user=u_id,version=version))


@training.route('/activate', methods=['GET', 'POST'])
@login_required
def activate_competence():
    """
    Method to change all assessments for a current competence to activated.

    :return:
    """
    u_id = request.args.get('u_id')
    c_id = request.args.get('c_id')
    print "LOOK AT ME"
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
            print i

@training.route('/four_year_activate/<c_id>', methods=['GET', 'POST'])
@login_required
def four_year_activate(c_id = None):
    """
    set all assessments in current competency to obselete and assign the latest version of
    the competency to the user - probably need to check if competence exists anymore?
    :return:
    """
    #get assessment ids for user and competence

    assessments = s.query(Assessments).\
        join(Subsection).\
        join(Competence).\
        join(AssessmentStatusRef).\
        filter(or_(AssessmentStatusRef.status == "Complete",AssessmentStatusRef.status == "Four Year Due")).\
        filter(Competence.id==c_id).\
        filter(Assessments.user_id == current_user.database_id).all()

    # set current assessments in this competency to obselete
    status_id = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Obsolete").first().id
    data = { 'status': status_id }
    for assessment in assessments:
        print "setting " + assessment.ss_id_rel.name + " to obsolete"
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
    four_years_ago = datetime.date.today() - relativedelta(months=48)

    print four_years_ago

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

            print send_mail(assessment.user_id ,"Four Year Competency Reassessment Required: "+ assessment.ss_id_rel.c_id_rel.competence_detail[0].title,"<br><br>".join(lines))

        done.append(str(assessment.user_id) + ":" + str(assessment.ss_id_rel.c_id))

    s.commit()




