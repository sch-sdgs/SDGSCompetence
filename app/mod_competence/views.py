from collections import OrderedDict

from flask import Blueprint, jsonify
from flask_table import Table, Col, ButtonCol
from sqlalchemy import and_, or_, case, func
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import get_competence_from_subsections, admin_permission
from app.models import *
from app.competence import s,send_mail
from app import config
from forms import *
import json
from app.qpulseweb import *
from app.qpulse_details import QpulseDetails
from collections import defaultdict
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from app.views import index

competence = Blueprint('competence', __name__, template_folder='templates')


class DeleteCol(Col):
    def __init__(self, name, attr=None, attr_list=None, **kwargs):
        super(DeleteCol, self).__init__(
            name,
            attr=attr,
            attr_list=attr_list,
            **kwargs)

    def td_contents(self, item, attr_list):
        print item
        return '<a href="#" class="remove btn btn-sm btn-danger" id="' + str(
            item.id) + '"><span class="glyphicon glyphicon-remove"></span></a>'


class ItemTableSubsections(Table):
    name = Col('Area of Competence')
    type = Col('Evidence Type')
    comments = Col('Comments')
    id = DeleteCol('Remove')


class ItemTableDocuments(Table):
    qpulseno = Col('QPulse ID')
    title = Col('QPulse Document Title')


@competence.route('/remove', methods=['GET', 'POST'])
def remove_subsection():
    print "HELLO"
    id = request.args["id"]
    version = request.args["version"]
    data = {
        'last': int(version)-1
    }
    s.query(Subsection).filter(Subsection.id == id).update(data)
    try:
        s.commit()
        return "True"
    except:
        return "False"


@competence.route('/list', methods=['GET', 'POST'])
def list_comptencies(message=None, modifier=None):
    previous_data = s.query(CompetenceDetails).join(Competence).filter(
        Competence.current_version > CompetenceDetails.intro).all()
    current_data = s.query(CompetenceDetails).join(Competence).filter(
        Competence.current_version == CompetenceDetails.intro).all()
    in_progress = s.query(CompetenceDetails).join(Competence).filter(
        Competence.current_version + 1 == CompetenceDetails.intro).all()
    return render_template('competences_list.html', current_data=current_data, previous_data=previous_data,
                           in_progress=in_progress, message=message, modifier=modifier)


@competence.route('/competent_staff', methods=['GET', 'POST'])
def competent_staff():
    ids = request.args["ids"].split(",")

    competent_staff = s.query(Assessments).join(Subsection).join(Competence).join(CompetenceDetails).filter(
        Competence.id.in_(ids)).filter(Users.active == True).filter(
        Assessments.status == 3).all()

    result = {}
    competence = s.query(Competence).join(CompetenceDetails).filter(Competence.id.in_(ids)).group_by(
        CompetenceDetails.id).all()
    for k in competence:
        print k.competence_detail[0].title
        result[k.competence_detail[0].title] = {}

        subsections = s.query(Subsection).filter_by(c_id=k.id).all()
        for j in subsections:
            print j.name
            if j.s_id_rel.name not in result[k.competence_detail[0].title]:
                result[k.competence_detail[0].title][j.s_id_rel.name] = {}
            if j.name not in result[k.competence_detail[0].title][j.s_id_rel.name]:

                result[k.competence_detail[0].title][j.s_id_rel.name][j.name]=[]

    print competent_staff
    print result
    for i in competent_staff:

        if i.user_id_rel.active:
            c_name = i.ss_id_rel.c_id_rel.competence_detail[0].title
            print c_name
            ss_name = i.ss_id_rel.name
            print i.ss_id_rel.s_id_rel.name
            print ss_name
            result[c_name][i.ss_id_rel.s_id_rel.name][ss_name].append(i)

    return render_template('competent_staff.html', result=result)


@competence.route('/activate', methods=['GET', 'POST'])
def activate():
    ids = request.args["ids"].split(",")
    for id in ids:
        count = s.query(Competence).join(CompetenceDetails).filter(Competence.id == id).group_by(
            CompetenceDetails.id).filter(CompetenceDetails.creator_id == current_user.database_id).count()
        if count == 1:
            s.query(Competence).filter_by(id=int(id)).update({"obsolete": False})
            s.commit()
        else:
            pass

    return redirect(url_for('competence.list_comptencies'))


@competence.route('/deactivate', methods=['GET', 'POST'])
def deactivate():
    ids = request.args["ids"].split(",")
    for id in ids:
        count = s.query(Competence).join(CompetenceDetails).filter(Competence.id == id).group_by(
            CompetenceDetails.id).filter(CompetenceDetails.creator_id == current_user.database_id).count()
        if count == 1:
            s.query(Competence).filter_by(id=int(id)).update({"obsolete": True})
            s.commit()
        else:
            pass

    return redirect(url_for('competence.list_comptencies'))


@competence.route('/add', methods=['GET', 'POST'])
def add_competence():
    form = AddCompetence()
    if request.method == 'POST':
        title = request.form['title'].replace(":", "-")
        scope = request.form['scope']
        val_period = request.form['validity_period']
        comp_category = request.form['competency_type']
        firstname, surname = request.form['approval'].split(" ")
        approval_id = int(s.query(Users).filter_by(first_name=firstname, last_name=surname).first().id)
        com = Competence()
        s.add(com)
        s.commit()

        c = CompetenceDetails(c_id=com.id,
                              title=title,
                              scope=scope,
                              creator_id=current_user.database_id,
                              validity_period=val_period,
                              category_id=comp_category,
                              intro=1,
                              approve_id=approval_id,
                              approved=None)
        s.add(c)
        s.commit()
        c_id = c.id

        if config.QPULSE_MODULE != False:
            doclist = request.form['doc_list'].split(',')
            for doc in doclist:
                add_doc = Documents(c_id=c_id, qpulse_no=doc)
                s.add(add_doc)

        s.commit()

        add_section_form = AddSection()

        constants = s.query(Section).filter(Section.constant == 1).all()
        result = {}
        for section in constants:
            if section.name not in result:
                result[section.name] = {'id': str(section.id), 'subsections': []}
            subsections = s.query(ConstantSubsections).filter_by(s_id=section.id).all()
            result[section.name]['subsections'].append(subsections)
            print(result[section.name]['subsections'])

            # print request.form(dir())
        # return render_template('competence_section.html', form=add_section_form, c_id=c_id, result=result)
        return render_template('competence_section.html', form=add_section_form, c_id=com.id, result=result)

    if config.QPULSE_MODULE == False:
        form.documents.render_kw = {'disabled': 'disabled'}
        form.add_document.render_kw = {'disabled': 'disabled'}

    return render_template('competence_add.html', form=form, qpulse_module=config.QPULSE_MODULE)


@competence.route('/addsections', methods=['GET', 'POST'])
def add_sections():
    print "hello"

    f = request.form
    c_id = request.args.get('c_id')
    for key in f.keys():
        if "subsections" in key:
            print(key)
            print(len(f.getlist(key)))
            for value in f.getlist(key):
                print key, ":", value
                s_id = key[0]
                item_add = s.query(ConstantSubsections.item).filter_by(id=value).first().item
                evidence = s.query(EvidenceTypeRef.id).filter_by(type='Discussion').first().id
                print "ITS HERE"
                print item_add
                add_constant = Subsection(c_id=c_id, s_id=s_id, name=item_add, evidence=evidence, comments=None)
                s.add(add_constant)
                s.commit()

    ###This section pulls the entire competence into the view once created.
    version = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).order_by(
        CompetenceDetails.intro.desc()).first().intro
    return redirect(url_for('competence.view_competence') + "?c_id=" + str(c_id) + "&version=" + str(version))

    ##Comptetence Details

    # get_comp_title = s.query(CompetenceDetails.title).filter_by(c_id=c_id).first()
    # comp_title = ','.join(repr(x.encode('utf-8')) for x in get_comp_title).replace("'", "")
    #
    # get_comp_scope = s.query(CompetenceDetails.scope).filter_by(c_id=c_id).first()
    # comp_scope = ','.join(repr(x.encode('utf-8')) for x in get_comp_scope).replace("'", "")
    #
    # get_comp_category = s.query(CompetenceCategory.category).join(CompetenceDetails).filter_by(c_id=c_id).first()
    # comp_category = ','.join(repr(x.encode('utf-8')) for x in get_comp_category).replace("'", "")
    #
    # get_comp_val_period = s.query(ValidityRef.months).join(CompetenceDetails).filter_by(c_id=c_id).first()
    # comp_val_period = int(get_comp_val_period[0])
    #
    # ##Creates a dictionary of the docs associated with a created competence
    # dict_docs = {}
    # docs = s.query(Documents.qpulse_no).join(CompetenceDetails).filter_by(c_id=c_id)
    # for doc in docs:
    #     doc_id = ','.join(repr(x.encode('utf-8')) for x in doc).replace("'", "")
    #     d = QpulseDetails()
    #     details = d.Details()
    #     username = str(details[1])
    #     password = str(details[0])
    #     q = QPulseWeb()
    #     doc_name = q.get_doc_by_id(username=username, password=password, docNumber=doc)
    #
    #     print doc_id
    #     dict_docs[doc_id] = doc_name
    #
    # ##Get subsection details
    # dict_subsecs = {}
    # subsections = get_subsections(c_id,version=0)
    # for item in subsections:
    #     sec_name = item.sec_name
    #     subsection_name = item.subsec_name
    #     comment = item.comments
    #     evidence_type = item.type
    #     subsection_data = [subsection_name, comment, evidence_type]
    #     print subsection_data
    #     dict_subsecs.setdefault(sec_name, []).append(subsection_data)
    # print dict_subsecs
    #
    # dict_constants = {}
    # constants = get_constant_subsections(c_id,version=0)
    # for item in constants:
    #     constant_sec_name = item.sec_name
    #     constant_subsection_name = item.subsec_name
    #     constant_comment = item.comments
    #     constant_evidence_type = item.type
    #     constant_subsection_data = [constant_subsection_name, constant_comment, constant_evidence_type]
    #     print constant_subsection_data
    #     dict_constants.setdefault(constant_sec_name, []).append(constant_subsection_data)
    # print "###CONSTANTS###"
    # print dict_constants
    #
    # return render_template('competence_view.html', c_id=c_id, title=comp_title, scope=comp_scope,
    #                        category=comp_category, val_period=comp_val_period, docs=dict_docs, constants=dict_constants,
    #                        subsections=dict_subsecs, version=version)


#todo - competence lifecycle:
#create a competence - and approve - everything is at v1
#edit the competence - everything gets copied and is at v2 - if you then delete last is v2 - but this is an issue.

def get_subsections(c_id, version):
    subsec_list = []
    subsecs = s.query(Subsection).join(Section).join(Competence).join(EvidenceTypeRef).filter(
        Subsection.c_id == c_id).filter(Section.constant == 0).filter(
        and_(Subsection.intro <= version, or_(Subsection.last == None, Subsection.last == version))).values(
        Section.name.label('sec_name'), Subsection.name.label('subsec_name'),
        Subsection.comments, EvidenceTypeRef.type)
    for sub in subsecs:
        subsec_list.append(sub)
    return subsec_list


def get_constant_subsections(c_id, version):
    constant_subsec_list = []
    constant_subsecs = s.query(Subsection).join(Section).join(Competence).join(EvidenceTypeRef).filter(
        Subsection.c_id == c_id).filter(Section.constant == 1).filter(
        and_(Subsection.intro <= version, or_(Subsection.last == None, Subsection.last == version))).values(
        Section.name.label('sec_name'), Subsection.name.label('subsec_name'),
        Subsection.comments, EvidenceTypeRef.type)
    for constant_sub in constant_subsecs:
        constant_subsec_list.append(constant_sub)
    return constant_subsec_list




@competence.route('/get_constant_subsections',methods=['GET', 'POST'])
def get_constant_subsections_web():
    id = request.args["id"]
    result = []
    subsections = s.query(ConstantSubsections).filter(ConstantSubsections.s_id==id).all()
    for subsection in subsections:
        print subsection.s_id
        result.append({"name":subsection.item,"id":subsection.id})
    return jsonify({"response":result})


@competence.route('/activate_comp', methods=['GET', 'POST'])
def activate_competency():
    c_id = request.json['c_id']
    # UPDATE Competence SET Competence.current_version = 1 WHERE Competence.id=c_id
    s.query(Competence).filter_by(id=c_id).update({"current_version": 1})
    s.commit()
    return jsonify({"response":'Competence has been activated!'})


@competence.route('/section', methods=['GET', 'POST'])
def get_section():
    if request.method == 'POST':
        # add subsection section database
        pass
    text = request.json['text']

    c_id = request.json['c_id']
    val = request.json['val']
    form = SectionForm()
    subsection_form = AddSubsection()
    # method below gets the subsections for the section_id selected in the form
    result_count = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        and_(Competence.id == c_id, Section.id == val)).count()
    if result_count != 0:
        result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
            and_(Competence.id == c_id, Section.id == val)).values(Subsection.name, EvidenceTypeRef.type,
                                                                   Subsection.comments)

        table = ItemTableSubsections(result,
                                     classes=['table', 'table-striped', 'table-bordered', 'section_' + str(val)])
    else:
        table = '<table class="section_' + str(val) + '"></table>'

    # print str(c_id) + ' ' + str(val) + ' ' + 'should get subsections for selected section'
    return jsonify({"response":render_template('section.html', c_id=c_id, form=form, val=val, text=text, table=table,
                                   subsection_form=subsection_form)})


@competence.route('/delete_subsection', methods=['GET', 'POST'])
def delete_subsection():
    print request.json
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    s.query(Subsection).filter_by(c_id=request.json['c_id']).filter_by(id=request.json["id"]).delete()
    s.commit()
    result_count = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        and_(Competence.id == c_id, Section.id == s_id)).count()
    if result_count != 0:
        result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
            and_(Competence.id == c_id, Section.id == s_id)).values(Subsection.id, Subsection.name,
                                                                    EvidenceTypeRef.type,
                                                                    Subsection.comments)

        table = ItemTableSubsections(result,
                                     classes=['table', 'table-striped', 'table-bordered', 'section_' + str(s_id)])
    else:
        table = '<table class="section_' + str(s_id) + '"></table>'
    return jsonify({"response":table})


@competence.route('/add_subsection_to_db', methods=['GET', 'POST'])
def add_sections_to_db():
    # method adds subsections to database
    name = request.json['name']
    evidence_id = request.json['evidence_id']
    comments = request.json['comments']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    print "IS IT HERE"
    print name
    print request.json
    if "version" in request.json:
        version = request.json['version']
    else:
        version = 1

    sub = Subsection(name=name, evidence=int(evidence_id), comments=comments, c_id=c_id, s_id=s_id,intro=version)
    s.add(sub)
    s.commit()
    result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        Competence.id == c_id).filter(Section.id == s_id). \
        values(Subsection.id, Subsection.name, EvidenceTypeRef.type, Subsection.comments)

    table = ItemTableSubsections(result, classes=['table', 'table-bordered', 'table-striped', 'section_' + str(s_id)])
    # print str(c_id) + ' ' + str(s_id) + ' ' + 'should add new subsection to selected section'
    if "plain" in request.args:
        return jsonify({'id':s_id})
    else:
        return jsonify({"response":table})


@competence.route('/add_constant_subsection_to_db', methods=['GET', 'POST'])
def add_constant_sections_to_db():
    name = request.json['name']
    id = request.json['id']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    version = request.json['version']
    print "HERE"
    print name
    if type(name) != unicode:
        name = name[0]
    else:
        name = name

    print name

    sub = Subsection(name=name, c_id=c_id, s_id=s_id, evidence=4, comments=None, intro=version)
    s.add(sub)
    s.commit()
    return jsonify({'id': sub.id})

@competence.route('/autocomplete_docs', methods=['GET'])
def document_autocomplete():
    doc_id = request.args.get('add_document')

    docs = s.query(Documents.qpulse_no).distinct()
    doc_list = []
    for i in docs:
        print(i)
        doc_list.append(i.qpulse_no)

    return jsonify(json_list=doc_list)


@competence.route('/autocomplete_competence', methods=['GET'])
def competence_name_autocomplete():
    competencies = s.query(CompetenceDetails).join(Competence).filter(
        Competence.current_version == CompetenceDetails.intro).all()
    competence_list = []
    for i in competencies:
        competence_list.append(i.category_rel.category + ": " + i.title)
        # competence_list.append({"label":i.category_rel.category + ": " + i.title,"value":i.id})

    return jsonify(json_list=competence_list)


@competence.route('/get_docs', methods=['GET'])
def get_documents(c_id):
    c_id = 1
    docid = request.json['add_document']
    documents = s.query(Documents).join(Competence).filter(competence.id == c_id)
    table = ItemTableDocuments(documents, classes=['table', 'table-striped', docid])
    return jsonify({"response":table})


@competence.route('/get_doc_name', methods=['POST', 'POST'])
def get_doc_name(doc_id=None):
    d = QpulseDetails()
    details = d.Details()
    username = str(details[1])
    password = str(details[0])
    q = QPulseWeb()
    if not doc_id:
        doc_id = request.json['doc_id']
        doc_name = q.get_doc_by_id(username=username, password=password, docNumber=doc_id)
        if doc_name == "False":
            return jsonify({"response":"This is not a valid QPulse Document"})
        else:
            return jsonify({"response":doc_name})

    else:
        doc_name = q.get_doc_by_id(username=username, password=password, docNumber=doc_id)
        return doc_name


@competence.route('/remove_doc', methods=['POST', 'POST'])
def remove_doc():
    c_id = request.args["c_id"]
    doc_number = request.args["doc_number"]
    print c_id
    print doc_number
    s.query(Documents).filter(and_(Documents.c_id == c_id, Documents.qpulse_no == doc_number)).delete()
    s.commit()
    return jsonify({"success": True})


@competence.route('/add_doc', methods=['POST', 'POST'])
def add_doc():
    c_id = request.args["c_id"]
    doc_number = request.args["doc_number"]

    if s.query(Documents).filter(and_(Documents.c_id == c_id, Documents.qpulse_no == doc_number)).count() == 0:
        doc = Documents(c_id=c_id, qpulse_no=doc_number)
        s.add(doc)
        s.commit()
        return jsonify({"success": True})


# in jquery - if doc_name is not null, add doc name to list associated documents
# -if doc name is null, state "This is not an existing document in Qpulse"

@competence.route('/add_constant', methods=['GET', 'POST'])
def add_constant_subsection():
    s_id = request.json['s_id']
    item = request.json['item']
    print "HELLO HERE"
    print item
    add_constant = ConstantSubsections(s_id=s_id, item=item)
    s.add(add_constant)
    s.commit()
    return jsonify({"response":add_constant.id})


@competence.route('/view_competence', methods=['GET', 'POST'])
def view_competence():
    c_id = request.args["c_id"]
    version = request.args["version"]
    get_comp_title = s.query(CompetenceDetails.title).filter_by(c_id=c_id).filter(
        CompetenceDetails.intro == version).first()
    comp_title = ','.join(repr(x.encode('utf-8')) for x in get_comp_title).replace("'", "")

    get_comp_scope = s.query(CompetenceDetails.scope).filter_by(c_id=c_id).filter(
        CompetenceDetails.intro == version).first()
    comp_scope = ','.join(repr(x.encode('utf-8')) for x in get_comp_scope).replace("'", "")

    get_comp_category = s.query(CompetenceCategory.category).join(CompetenceDetails).filter_by(c_id=c_id).filter(
        CompetenceDetails.intro == version).first()
    comp_category = ','.join(repr(x.encode('utf-8')) for x in get_comp_category).replace("'", "")

    get_comp_val_period = s.query(ValidityRef.months).join(CompetenceDetails).filter_by(c_id=c_id).filter(
        CompetenceDetails.intro == version).first()

    approved = s.query(CompetenceDetails).filter_by(c_id=c_id).filter(
        CompetenceDetails.intro == version).first().approved
    id = s.query(CompetenceDetails).filter_by(c_id=c_id).filter(
        CompetenceDetails.intro == version).first().id

    comp_val_period = int(get_comp_val_period[0])

    ##Creates a dictionary of the docs associated with a created competence
    dict_docs = {}
    docs = s.query(Documents.qpulse_no).join(CompetenceDetails).filter(CompetenceDetails.intro == version).filter_by(
        c_id=c_id)
    for doc in docs:
        doc_id = ','.join(repr(x.encode('utf-8')) for x in doc).replace("'", "")
        d = QpulseDetails()
        details = d.Details()
        username = str(details[1])
        password = str(details[0])
        q = QPulseWeb()
        doc_name = q.get_doc_by_id(username=username, password=password, docNumber=doc)

        print doc_id
        dict_docs[doc_id] = doc_name

    ##Get subsection details
    dict_subsecs = {}
    subsections = get_subsections(c_id, version)
    for item in subsections:
        sec_name = item.sec_name
        subsection_name = item.subsec_name
        comment = item.comments
        evidence_type = item.type
        subsection_data = [subsection_name, comment, evidence_type]
        print subsection_data
        dict_subsecs.setdefault(sec_name, []).append(subsection_data)
    print dict_subsecs

    dict_constants = {}
    constants = get_constant_subsections(c_id, version)
    for item in constants:
        constant_sec_name = item.sec_name
        constant_subsection_name = item.subsec_name
        constant_comment = item.comments
        constant_evidence_type = item.type
        constant_subsection_data = [constant_subsection_name, constant_comment, constant_evidence_type]
        print constant_subsection_data
        dict_constants.setdefault(constant_sec_name, []).append(constant_subsection_data)
    print "###CONSTANTS###"
    print dict_constants

    return render_template('competence_view.html', c_id=c_id, title=comp_title, version=version, scope=comp_scope,
                           category=comp_category, val_period=comp_val_period, docs=dict_docs, constants=dict_constants,
                           subsections=dict_subsecs, review="yes", approved=approved, id=id)


@competence.route('/send_for_approval', methods=['GET'])
def send_for_approval():
    id = request.args["id"]
    s.query(CompetenceDetails).filter(CompetenceDetails.id == id).update({"approved": 0})
    s.commit()
    competence = s.query(CompetenceDetails).filter(CompetenceDetails.id == id).first()
    send_mail(competence.approve_id, "Competence awaiting your approval","You have a competence written by <b>" + current_user.full_name + "</b> to approve.")

    return json.dumps({"success": True})

@competence.route('/force_approve')
def force_authorise():

    check = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == request.args["id"]).first()
    if check.approved != 1:
        approve(id=request.args["id"],version=request.args["version"],u_id=current_user.database_id)
        return list_comptencies(message="<strong>Success!</strong> Competencies Force Authorised",modifier="success")
    else:
        return list_comptencies(message="<strong>Warning!</strong> Competencies Already Authorised",modifier="warning")




@competence.route('/approve/<id>/<version>/<u_id>', methods=['GET'])
def approve(id=None, version=None, u_id=None):
    user_allowed = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
        CompetenceDetails.intro == version).first().approve_id
    creator = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
        CompetenceDetails.intro == version).first()
    full_name = creator.creator_rel.first_name + " " + creator.creator_rel.last_name
    if user_allowed == int(u_id):
        ok_go = True
    elif "ADMIN" in current_user.roles:
        ok_go = True
    else:
        ok_go = False


    if ok_go == True:
        # update competence details with approval information
        data = {
            "approve_id": current_user.database_id,
            "date_of_approval": datetime.date.today(),
            "approved": True

        }
        s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
            CompetenceDetails.intro == version).update(data)
        s.commit()

        # todo: should editing the details do this?
        # update competence details for last version
        data = {
            "last": int(version) - 1
        }
        s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
            CompetenceDetails.intro == int(version) - 1).update(data)
        s.commit()

        # update competence master table with current version
        data = {
            "current_version": version
        }
        s.query(Competence).filter(Competence.id == id).update(data)

        # make the creator competent
        # print "hello"
        # make_user_competent(ids=[int(id)],users=[full_name])
        s.commit()



    else:
        print "not allowed"

    competence = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(CompetenceDetails.intro == version).first()
    send_mail(competence.creator_id, "Competence Approved!",
              "Your competence \""+competence.title+"\" has been approved by <b>" + current_user.full_name)

    #return json.dumps({"success": True})
    return redirect('/')

@competence.route('/reject/<id>/<version>/<u_id>', methods=['GET'])
def reject(id=None, version=None, u_id=None):
    user_allowed = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
        CompetenceDetails.intro == version).first().approve_id
    creator = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
        CompetenceDetails.intro == version).first()
    full_name = creator.creator_rel.first_name + " " + creator.creator_rel.last_name
    if user_allowed == int(u_id):
        data = {
            "approve_id": u_id,
            "approved": None

        }
        s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
            CompetenceDetails.intro == version).update(data)
        s.commit()

        competence = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).filter(
            CompetenceDetails.intro == version).first()
        send_mail(competence.creator_id, "Competence Rejected!",
                  "Your competence \"" + competence.title + "\" has been rejected by <b>" + current_user.full_name)

        # return json.dumps({"success": True})
        return redirect('/')


@competence.route('/check_exists', methods=['GET', 'POST'])
def check_exists():
    if request.method == 'POST':
        if ":" in request.form["name"]:
            category, competence = request.form["name"].split(": ")
            c_query = s.query(Competence).join(CompetenceDetails).filter(CompetenceDetails.title == competence).first()
            if c_query:
                return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@competence.route('/assign_user_to_competence', methods=['GET', 'POST'])
def assign_user_to_competence():
    ids = request.args["ids"].split(",")
    print ids
    if request.method == 'POST':
        print request.form["name"]
        category, competence = request.form["name"].split(": ")
        cat_id = s.query(CompetenceCategory).filter_by(category=category).first().id
        c_query = s.query(Competence).join(CompetenceDetails).filter(CompetenceDetails.title == competence).filter(
            CompetenceDetails.category_id == cat_id).first()
        c_id = c_query.id

        for user_id in ids:
            assign_competence_to_user(int(user_id), int(c_id))
        return "True"

    else:
        form = AssignForm()
        query = s.query(Users).filter(Users.id.in_(ids)).values(Users.first_name, Users.last_name)
        assignees = []
        for i in query:
            assignees.append(i.first_name + " " + i.last_name)

        return render_template('competence_assign.html', form=form, assignees=", ".join(assignees),
                               ids=request.args["ids"])


@competence.route('/assign_competences_to_user', methods=['GET', 'POST'])
def assign_competences_to_user():
    form = UserAssignForm()

    ids = request.args["ids"].split(",")

    if request.method == 'POST':
        users = request.form["user_list"].split(",")
        result = {}
        for user in users:
            failed = []
            if user not in result:
                result[user] = []
            firstname, surname = user.split()
            count = s.query(Users).filter_by(first_name=firstname, last_name=surname).count()
            if count > 0:
                user_id = int(s.query(Users).filter_by(first_name=firstname, last_name=surname).first().id)
                for c_id in ids:
                    final_id = assign_competence_to_user(user_id, int(c_id))
                    print final_id
                    if final_id:
                        comp = s.query(Assessments).filter(Assessments.id.in_(final_id)).first()
                        current_version = s.query(Competence).filter(
                            Competence.id == comp.ss_id_rel.c_id).first().current_version
                        for i in comp.ss_id_rel.c_id_rel.competence_detail:
                            if i.intro == current_version:
                                result[user].append(dict(comptence=i.title, success=True))
            else:
                failed.append(user)
                failed.append(user)

        return render_template('competence_assigned.html', result=result, failed=failed)
    else:
        query = s.query(Competence).join(CompetenceDetails).filter(Competence.id.in_(ids)).filter(
            Competence.current_version == CompetenceDetails.intro).values(CompetenceDetails.title)
        comptences = []
        for i in query:
            print i.title
            comptences.append(i.title)

        return render_template('competence_user_assign.html', form=form, competences=", ".join(comptences),
                               ids=request.args["ids"])


@competence.route('/make_user_competent', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def make_user_competent(ids=None,users=None):
    form = UserAssignForm()

    if ids == None:
        ids = request.args["ids"].split(",")
    if request.method == 'POST':
        if users == None:
            users = request.form["user_list"].split(",")
        result = {}
        for user in users:
            failed = []
            if user not in result:
                result[user] = []
            firstname, surname = user.split()
            count = s.query(Users).filter_by(first_name=firstname, last_name=surname).count()
            if count > 0:
                user_id = int(s.query(Users).filter_by(first_name=firstname, last_name=surname).first().id)
                for c_id in ids:
                    final_ids = assign_competence_to_user(user_id, int(c_id))
                    print "THIS ONE"
                    print final_ids
                    if final_ids is not None:

                        for ass_id in final_ids:
                            status_id = s.query(AssessmentStatusRef).filter(
                                AssessmentStatusRef.status == "Complete").first().id
                            data = {'trainer_id': current_user.database_id,
                                    'date_of_training': datetime.date.today(),
                                    'date_completed': datetime.date.today(),
                                    #todo make this expiry the length of the competence
                                    #datetime.date.today() + relativedelta(months=+6)
                                    'date_expiry': dt.strptime('Dec 1 2200', '%b %d %Y'),
                                    'date_activated': datetime.date.today(),
                                    'signoff_id': current_user.database_id,
                                    'status': status_id,
                                    }
                            print "hello"
                            print data
                            s.query(Assessments).filter(Assessments.id == ass_id).update(data)
                            s.commit()

                        comp = s.query(Competence).join(CompetenceDetails).filter(Competence.id == int(c_id)).first()
                        print comp.competence_detail
                        result[user].append(dict(comptence=comp.competence_detail[0].title, success=True))
                    else:
                        print "fail"
                        return redirect(url_for('index'))
            else:
                failed.append(user)
                failed.append(user)
        if ids == None:
            return render_template('competence_assigned.html', result=result, failed=failed)
        else:
            print "HERE"
            return render_template('competence_assigned.html', result=result, failed=failed)
    else:
        print "oh dear"
        query = s.query(Competence).join(CompetenceDetails).filter(Competence.id.in_(ids)).values(
            CompetenceDetails.title)
        comptences = []
        for i in query:
            print i.title
            comptences.append(i.title)

        return render_template('competence_override.html', form=form, competences=", ".join(comptences),
                               ids=request.args["ids"])


def assign_competence_to_user(user_id, competence_id):
    status_id = s.query(AssessmentStatusRef).filter_by(status="Assigned").first().id
    # TODO Not Working
    # gets subsections for competence
    current_version = s.query(Competence).filter(Competence.id == competence_id).first().current_version
    sub_sections = s.query(Subsection).filter(Subsection.c_id == competence_id).filter(
        or_(Subsection.last == None, Subsection.last == current_version)).filter(
        Subsection.intro <= current_version).all()
    print "YOYOYO"
    print sub_sections
    sub_list = []

    print sub_sections
    # TODO Check if competence is already assigned, if it is skip user and display warning
    # TODO Need to add competence constant subsections

    for sub_section in sub_sections:
        sub_list.append(sub_section.id)

    assessment_ids = []
    check = s.query(Assessments).filter(Assessments.ss_id.in_(sub_list)).filter_by(user_id=user_id).filter(
        Assessments.version == current_version).count()
    if check == 0:
        for sub_section in sub_sections:
            print sub_section
            a = Assessments(status=status_id, ss_id=sub_section.id, user_id=int(user_id),
                            assign_id=current_user.database_id, version=current_version)
            print a
            s.add(a)
            s.commit()
            assessment_ids.append(a.id)

        assigner = s.query(Users).filter(Users.id == current_user.database_id).first()
        try:
            send_mail(user_id,"Competence has been assigned to you","You have been assigned a competence by <b>"+assigner.first_name + " " + assigner.last_name +"</b>")
        except:
            s.rollback()
    else:
        assessment_ids = None
    print "i did this"
    return assessment_ids


@competence.route('/edit', methods=['GET', 'POST'])
def edit_competence():
    ids = request.args.get('ids').split(",")
    # todo: CHECK HERE IF COMPETENCE IS IN APPROVAL???

    c_id = ids[0]
    # test_id = '18'

    form = EditCompetency()
    subsection_form = AddSubsection()
    section_form = AddSection()
    # get basic details for competence
    live = False
    current_version = s.query(Competence).filter(Competence.id == c_id).first().current_version
    if current_version:
        live = True

    comp_category = s.query(CompetenceCategory).join(CompetenceDetails).filter_by(c_id=c_id).order_by(
        CompetenceDetails.intro.desc()).first()
    form.edit_competency_type.choices = s.query(CompetenceCategory).values(CompetenceCategory.id,
                                                                           CompetenceCategory.category)
    form.edit_competency_type.default = comp_category.id

    comp_val_period = s.query(ValidityRef).join(CompetenceDetails).filter_by(c_id=c_id).order_by(
        CompetenceDetails.intro.desc()).first()

    form.edit_validity_period.choices = s.query(ValidityRef).values(ValidityRef.id, ValidityRef.months)
    form.edit_validity_period.default = comp_val_period.id

    form.process()

    comp = s.query(CompetenceDetails).filter_by(c_id=c_id).order_by(CompetenceDetails.intro.desc()).first()
    # if comp.intro == current_version:
    #     print comp.asdict()
    form.edit_title.data = comp.title
    form.edit_scope.data = comp.scope

    form.approval.data = comp.approve_rel.first_name + " " + comp.approve_rel.last_name
    doc_query = s.query(Documents.qpulse_no).filter_by(c_id=comp.id).all()
    documents = []
    for i in doc_query:
        name = get_doc_name(doc_id=i)
        documents.append([i.qpulse_no, name])
    # get subsections
    sub_result = {}
    subsections = s.query(Subsection).filter(Subsection.c_id == c_id).filter(Subsection.last == None).all()
    for subsection in subsections:
        if subsection.s_id_rel.constant == 1:
            if "constant" not in sub_result:
                sub_result["constant"] = {}
            if (subsection.s_id_rel.name,subsection.s_id_rel.id) not in sub_result["constant"]:
                sub_result["constant"][(subsection.s_id_rel.name,subsection.s_id_rel.id)] = []
            sub_result["constant"][(subsection.s_id_rel.name,subsection.s_id_rel.id)].append(subsection)
        else:
            if "custom" not in sub_result:
                sub_result["custom"] = {}
            if (subsection.s_id_rel.name,subsection.s_id_rel.id) not in sub_result["custom"]:
                sub_result["custom"][(subsection.s_id_rel.name,subsection.s_id_rel.id)] = []
            sub_result["custom"][(subsection.s_id_rel.name,subsection.s_id_rel.id)].append(subsection)

    print sub_result
    competence_copy = create_copy_of_competence(c_id, current_version, comp.title, comp.scope, comp_val_period.id,
                                          comp.category_id, comp.approve_id)

    return render_template('competence_edit.html', c_id=c_id, form=form, live=live, detail_id=competence_copy[0],
                           subsections=sub_result, version=competence_copy[1], docs=json.dumps(documents),subsection_form=subsection_form,section_form=section_form)


def create_copy_of_competence(c_id, current_version, title, scope, valid, type, approve_id):
    print "hello"
    query = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).filter(
        CompetenceDetails.intro == current_version + 1).first()
    current = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).filter(
        CompetenceDetails.intro == current_version).first()
    print query
    if query is None:
        # make a copy of the competence
        c = CompetenceDetails(c_id=c_id, title=title, scope=scope, creator_id=current_user.database_id,
                              validity_period=valid, category_id=type, intro=current_version + 1,
                              approve_id=approve_id)
        s.add(c)
        s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).filter(
            CompetenceDetails.intro == current_version).update({"last": current_version})
        s.commit()

        # copy docs across to new competence
        print current.id
        current_docs = s.query(Documents).filter(Documents.c_id == current.id).all()
        for doc in current_docs:
            d = Documents(c_id=c.id, qpulse_no=doc.qpulse_no)
            s.add(d)
            s.commit()
        return (c.id,current_version+1)
    else:
        return (query.id,current_version+1)


@competence.route('/change_ownership', methods=['GET', 'POST'])
def change_ownership():
    #TODO: should this only change ownership of the most recent version
    form = UserAssignForm()
    ids = request.args['ids']
    if request.method == 'POST':
        name = request.form["full_name"]
        firstname, surname = name.split(" ")
        new_creator_id = int(s.query(Users).filter_by(first_name=firstname, last_name=surname).first().id)
        for id in ids.split(","):
            data = {"creator_id": new_creator_id}
            s.query(CompetenceDetails).filter(CompetenceDetails.c_id == id).update(data)

        try:
            s.commit()
            return list_comptencies(message="<b>Success!</b> Ownership change to " + name, modifier="success")
        except:
            return list_comptencies(message="<b>Failed!</b> Ownership change to " + name + "failed", modifier="danger")

    return render_template('competence_change_ownership.html', form=form, ids=ids)


@competence.route('/edit_details', methods=['GET', 'POST'])
def edit_details():
    c_id = request.args['c_id']
    version = request.args['version']
    title = request.form['edit_title']
    scope = request.form['edit_scope']
    firstname, surname = request.form['approval'].split(" ")
    valid = request.form['edit_validity_period']
    type = request.form['edit_competency_type']
    approve_id = int(s.query(Users).filter_by(first_name=firstname, last_name=surname).first().id)
    data = {"title": title,
            "scope": scope,
            "approve_id": approve_id,
            "validity_period": valid,
            "category_id": type}
    print data

    current_version = int(s.query(Competence).filter(Competence.id == c_id).first().current_version)
    print current_version
    # competence hasn't been made live yet - it's at version 0
    if current_version == 0:
        print "I AM HERE"
        try:
            s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).update(data)
            s.commit()
            return json.dumps({"success": True})
        except:
            print "fail"
    else:
        # check if a version exists above current version
        check = s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).filter(
            CompetenceDetails.intro == current_version + 1).count()
        if check == 0:
            # make a copy of the competence
            create_copy_of_competence(c_id, current_version, title, scope, valid, type, approve_id)
            # c = CompetenceDetails(c_id=c_id, title=title, scope=scope, creator_id=current_user.database_id,
            #                       validity_period=valid, category_id=type, intro=current_version + 1,
            #                       approve_id=approve_id)
            # s.add(c)
            # s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).filter(
            #     CompetenceDetails.intro == current_version).update({"last": current_version})
            # s.commit()

        s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).filter(
            CompetenceDetails.intro == current_version + 1).update(data)
        s.commit()
        return json.dumps({"success": True})


@competence.route('/delete', methods=['GET', 'POST'])
def delete():
    id = request.args.get('c_id')
    print id
    c_id = s.query(CompetenceDetails).filter(CompetenceDetails.id == id).first().c_id

    current_version = s.query(Competence).filter(Competence.id == c_id).first().current_version
    s.query(Documents).filter(Documents.c_id == id).delete()
    s.commit()
    s.query(CompetenceDetails).filter(CompetenceDetails.c_id == c_id).filter(
        CompetenceDetails.intro == current_version + 1).delete()
    s.commit()
    s.query(Subsection).filter(Subsection.c_id == c_id).filter(Subsection.intro == current_version + 1).delete()
    s.commit()
    if current_version == 0:
        s.query(Competence).filter(Competence.id == c_id).delete()
        s.commit()

    return json.dumps({'success': True})


def nearest(items, pivot):
    return min(items, key=lambda x: abs(x - pivot))


def reporting():
    counts = {}
    expired = {}
    expiring = {}
    user_expired = {}
    user_expiring = {}
    change = {}
    # get current
    services = s.query(Service).all()
    for i in services:
        service = i.name.replace(" ", "")
        counts[service] = dict()
        counts[service]["Complete"] = 0
        counts[service]["Sign-Off"] = 0
        counts[service]["Active"] = 0
        counts[service]["Assigned"] = 0
        counts[service]["Expiring"] = 0
        counts[service]["Expired"] = 0
        counts[service]["Abandoned"] = 0

        expired[service] = []
        expiring[service] = []

    for i in s.query(Assessments).all():
        print i
        print i.user_id_rel.serviceid
        print i.status_rel.status
        if i.user_id_rel.service_rel is not None:
            if i.user_id_rel.active == 1:
                service = i.user_id_rel.service_rel.name.replace(" ", "")
                fullname = i.user_id_rel.first_name + " " + i.user_id_rel.last_name
                if i.date_expiry is not None:
                    if datetime.date.today() > i.date_expiry:
                        counts[service]["Expired"] += 1
                        expired[service].append(i)

                        if fullname not in user_expired:
                            user_expired[fullname] = 1
                        else:
                            user_expired[fullname] += 1

                    elif datetime.date.today() + relativedelta(months=+6) > i.date_expiry:
                        counts[service]["Expiring"] += 1
                        expiring[service].append(i)
                        if fullname not in user_expiring:
                            user_expiring[fullname] = 1
                        else:
                            user_expiring[fullname] += 1
                    else:
                        counts[service][i.status_rel.status] += 1
                else:
                    counts[service][i.status_rel.status] += 1

    return [counts,expired,expiring,user_expired,user_expiring,change]

@competence.route('/report_by_section', methods=['GET', 'POST'])
def report_by_section():
    counts, expired, expiring, user_expired, user_expiring, change = reporting()

    # get historic
    all_reports_date = [r.date for r in s.query(MonthlyReportNumbers.date)]
    most_recent_data = nearest(all_reports_date, datetime.datetime.now())
    historic = s.query(MonthlyReportNumbers).filter(MonthlyReportNumbers.date == most_recent_data).order_by(
        MonthlyReportNumbers.service_id.asc()).all()

    # for count in counts:

    return render_template('competence_report_by_section.html', counts=counts, historic=historic, expired=expired,
                           expiring=expiring,
                           user_expired=sorted(user_expired.items(), key=lambda key: key[1], reverse=True)[:5],
                           user_expiring=sorted(user_expiring.items(), key=lambda key: key[1], reverse=True)[:5])


@competence.route('/history', methods=['GET', 'POST'])
def competence_history():
    events = {}
    ids = request.args.get('ids').split(",")
    c_id = ids[0]
    print c_id
    competence = s.query(Competence).filter(Competence.id == c_id).first()
    version = competence.current_version
    title = {}

    print competence.competence_detail

    for count, i in enumerate(competence.competence_detail):
        if i.date_of_approval is not None:
            if i.date_of_approval not in events:
                events[i.date_of_approval] = []
            events[i.date_of_approval].append(["Release", "<b>Version " + str(
                i.intro) + " was released!</b> Approved by " + i.approve_rel.first_name + " " + i.approve_rel.last_name,
                                               None])

        if i.date_created not in events:
            events[i.date_created] = []

        print "count " + str(count) + " title " + i.title + " intro " + str(i.intro)

        ss = []

        title["current"] = i.title

        print title
        if "previous" in title and "current" in title:
            if title["previous"] != title["current"]:
                ss.append('<h4>Title Edited</h4>')
                ss.append('<p class="text-green">+ ' + title["current"] + "</p>")
                ss.append('<p class="text-red">- ' + title["previous"] + "</p>")

        if i.intro > 1:
            subsections = s.query(Subsection).filter(Subsection.c_id == c_id).all()
            ss.append('<h4>Subsection(s) Edited</h4>')
            for j in subsections:
                if j.intro == i.intro:
                    ss.append('<p class="text-green">+ ' + j.name + "</p>")
                elif j.last == i.intro - 1:
                    ss.append('<p class="text-red">- ' + j.name + "</p>")
                    # elif j.last == version:
                    #     ss.append('<p class="text-red">- ' + j.name + "</p>")

            if i.date_of_approval in events:
                events[i.date_of_approval].append(
                    ["Edited", "<b>Edited by</b> " + i.creator_rel.first_name + " " + i.creator_rel.last_name, ss])
        else:
            events[i.date_created].append(["Created",
                                           "<b>" + i.title + "</b> created by " + i.creator_rel.first_name + " " + i.creator_rel.last_name,
                                           None])

        title["previous"] = i.title

        # these are current ongoing edits they are just assigned to todays date for display purposes
    subsections = s.query(Subsection).filter(Subsection.c_id == c_id).filter(Subsection.last == version).all()
    ss = []
    ss.append('<h4>Subsection(s) Edited</h4>')
    for j in subsections:
        ss.append('<p class="text-red">- ' + j.name + "</p>")
    if datetime.date.today() not in events:
        events[datetime.date.today()] = []

    events[datetime.date.today()].insert(0, ["Edited",
                                             "<b>Edited by</b> " + i.creator_rel.first_name + " " + i.creator_rel.last_name,
                                             ss])

    return render_template('competence_history.html',
                           events=OrderedDict(sorted(events.items(), key=lambda t: t[0], reverse=True)))



@competence.route('/videos', methods=['GET', 'POST'])
def videos():
    videos = s.query(Videos).all()
    return render_template("competence_videos.html",videos=videos)