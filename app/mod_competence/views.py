from collections import OrderedDict
from flask_table import Table, Col
from sqlalchemy import and_, or_, func, asc, desc
from flask import render_template, request, url_for, redirect, Blueprint, jsonify, flash, Markup
from flask_login import login_required, current_user
from app.views import admin_permission
from app.models import *
from app.competence import s,send_mail
from app.competence import config
from mod_competence.forms import *
import json
from app.qpulseweb import *
from datetime import datetime as dt
from dateutil.relativedelta import relativedelta
from app.views import index
import plotly.graph_objects as go
from plotly.offline import plot

competence = Blueprint('competence', __name__, template_folder='templates')

#TODO docstrings fo classes

class DeleteCol(Col):
    def __init__(self, name, attr=None, attr_list=None, **kwargs):
        super(DeleteCol, self).__init__(
            name,
            attr=attr,
            attr_list=attr_list,
            **kwargs)

    def td_contents(self, item, attr_list):
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
@login_required
def remove_subsection():
    """
    Remove a subsection from a competence
    """
    id = request.args["id"]
    version = request.args["version"]
    data = {
        'last': int(version)-1
    }
    s.query(Subsection). \
        filter(Subsection.id == id). \
        update(data)
    try:
        s.commit()
        return "True"
    except:
        return "False"


@competence.route('/list', methods=['GET', 'POST'])
@login_required
def list_comptencies(message=None, modifier=None):
    """
    List all competencies
    """
    previous_data = s.query(CompetenceDetails). \
        join(Competence). \
        filter(Competence.current_version > CompetenceDetails.intro). \
        all()
    current_data = s.query(CompetenceDetails). \
        join(Competence).filter(Competence.current_version == CompetenceDetails.intro). \
        all()
    in_progress = s.query(CompetenceDetails). \
        join(Competence). \
        filter(Competence.current_version + 1 == CompetenceDetails.intro). \
        all()

    return render_template('competences_list.html', current_data=current_data, previous_data=previous_data,
                           in_progress=in_progress, message=message, modifier=modifier)


@competence.route('/competent_staff', methods=['GET', 'POST'])
@login_required
def competent_staff():
    """Find all competent staff"""
    ids = request.args["ids"].split(",")
    version = request.args["version"]

    ### List competent staff for a given assessment
    competent_staff = s.query(Assessments). \
        join(Users, Users.id==Assessments.user_id). \
        join(AssessmentStatusRef). \
        join(Subsection). \
        join(Competence). \
        join(CompetenceDetails). \
        filter(Subsection.c_id.in_(ids)). \
        filter(Assessments.version == version). \
        filter(Users.active == True). \
        filter(or_(AssessmentStatusRef.status == "Complete",
                   AssessmentStatusRef.status == "Assigned",
                   AssessmentStatusRef.status == "Active",
                   AssessmentStatusRef.status=="Four Year Due")). \
        all()

    result = OrderedDict()

    ### Find the competence for a given assessment
    competence = s.query(Competence). \
        join(CompetenceDetails). \
        filter(Competence.id.in_(ids)). \
        filter(Competence.current_version == version). \
        group_by(CompetenceDetails.id). \
        all()

    ### Loop through competences and update dictionary
    for k in competence:
        result[k.competence_detail[0].title]= OrderedDict()
        result[k.competence_detail[0].title]["constant"] = OrderedDict()
        result[k.competence_detail[0].title]["custom"] = OrderedDict()

        ### Find competence subsection order
        for_order = s.query(SectionSortOrder). \
            filter(SectionSortOrder.c_id == k.id). \
            order_by(asc(SectionSortOrder.sort_order)). \
            all()

        ### Loop through subsection order and update dictionary
        for x in for_order:
            check = s.query(Subsection). \
                join(Competence). \
                filter(Subsection.s_id == x.section_id). \
                filter(and_(version <= Competence.current_version,
                            Subsection.intro <= version,
                            or_(Subsection.last > version,
                                Subsection.last == None))). \
                count()

            if check > 0 :
                if x.section_id_rel.constant == 1:
                    result[k.competence_detail[0].title]["constant"][x.section_id_rel.name] = OrderedDict()
                else:
                    result[k.competence_detail[0].title]["custom"][x.section_id_rel.name] = OrderedDict()

        ### Loop through subsections and update dictionary
        subsections = s.query(Subsection). \
            join(Competence). \
            filter(Subsection.c_id==k.id). \
            filter(and_(version <= Competence.current_version,
                        Subsection.intro <= version,
                        or_(Subsection.last >= version,
                            Subsection.last == None))). \
            all()

        for j in subsections:
            if j.s_id_rel.constant==1:
                if j.name not in result[k.competence_detail[0].title]["constant"][j.s_id_rel.name]:
                    result[k.competence_detail[0].title]["constant"][j.s_id_rel.name][j.name]=[]
            else:
                if j.name not in result[k.competence_detail[0].title]["custom"][j.s_id_rel.name]:
                    result[k.competence_detail[0].title]["custom"][j.s_id_rel.name][j.name] = []

    ### Loop through competent staff and update dictionary
    for i in competent_staff:
        if i.user_id_rel.active:
            c_name = i.ss_id_rel.c_id_rel.competence_detail[0].title
            ss_name = i.ss_id_rel.name
            if i.ss_id_rel.s_id_rel.name in result[c_name]["custom"]:
                if ss_name in result[c_name]["custom"][i.ss_id_rel.s_id_rel.name]:
                    result[c_name]["custom"][i.ss_id_rel.s_id_rel.name][ss_name].append(i)
            else:
                result[c_name]["constant"][i.ss_id_rel.s_id_rel.name][ss_name].append(i)

    return render_template('competent_staff.html', result=result)


@competence.route('/activate', methods=['GET', 'POST'])
@login_required
def activate():
    """
    activate a competency
    """
    ids = request.args["ids"].split(",")
    for id in ids:
        count = s.query(Competence). \
            join(CompetenceDetails). \
            filter(Competence.id == id). \
            group_by(CompetenceDetails.id). \
            filter(CompetenceDetails.creator_id == current_user.database_id). \
            count()
        if count == 1:
            s.query(Competence). \
                filter_by(id=int(id)). \
                update({"obsolete": False})
            s.commit()
        else:
            pass

    return redirect(url_for('competence.list_comptencies'))


@competence.route('/deactivate', methods=['GET', 'POST'])
@login_required
def deactivate():
    """
    deactivate a competency
    """
    ids = request.args["ids"].split(",")
    for id in ids:
        count = s.query(Competence). \
            join(CompetenceDetails). \
            filter(Competence.id == id). \
            group_by(CompetenceDetails.id). \
            filter(CompetenceDetails.creator_id == current_user.database_id). \
            count()
        if count == 1:
            s.query(Competence). \
                filter_by(id=int(id)). \
                update({"obsolete": True})
            s.commit()
        else:
            pass

    return redirect(url_for('competence.list_comptencies'))


@competence.route('/add', methods=['GET', 'POST'])
@login_required
def add_competence():
    """
    Add a new competency
    """
    form = AddCompetence()
    if request.method == 'POST':
        title = request.form['title'].replace(":", "-")
        scope = request.form['scope']
        val_period = request.form['validity_period']
        comp_category = request.form['competency_type']
        firstname, surname = request.form['approval'].split(" ")
        approval_id = int(s.query(Users). \
                          filter_by(first_name=firstname,
                                    last_name=surname). \
                          first(). \
                          id)
        com = Competence()
        s.add(com)
        s.commit()

        ### prevent resubmissions with a count
        if s.query(CompetenceDetails). \
                filter(CompetenceDetails.title == title). \
                count() != 0:
            flash("This competence already exists - please try editing the existing competence or deleting it!","danger")
            return index()

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

        ### add q-pulse information
        if config.get("QPULSE_MODULE") != False:
            doclist = request.form['doc_list'].split(',')
            for doc in doclist:
                add_doc = Documents(c_id=c_id, qpulse_no=doc)
                s.add(add_doc)

        s.commit()

        add_section_form = AddSection()

        constants = s.query(Section). \
            filter(Section.constant == 1). \
            all()
        result = {}
        for section in constants:
            if section.name not in result:
                result[section.name] = {'id': str(section.id), 'subsections': []}
            subsections = s.query(ConstantSubsections). \
                filter_by(s_id=section.id). \
                all()
            result[section.name]['subsections'].append(subsections)

        return render_template('competence_section.html', form=add_section_form, c_id=com.id, result=result)

    if config.get("QPULSE_MODULE") == False:
        form.documents.render_kw = {'disabled': 'disabled'}
        form.add_document.render_kw = {'disabled': 'disabled'}

    return render_template('competence_add.html', form=form, qpulse_module=config.get("QPULSE_MODULE"))


@competence.route('/addsections', methods=['GET', 'POST'])
@login_required
def add_sections():
    """
    Add sections to competence
    """
    f = request.form
    c_id = request.args.get('c_id')
    ss_sort_order=0
    for key in f.keys():
        if "subsections" in key:
            print(key)
            print(len(f.getlist(key)))
            for value in f.getlist(key):
                s_id = key.split("_")[0]
                item_add = s.query(ConstantSubsections.item).filter_by(id=value).first().item
                evidence = s.query(EvidenceTypeRef.id).filter_by(type='Discussion').first().id
                ss_sort_order+=1
                add_constant = Subsection(c_id=c_id, s_id=s_id, name=item_add, evidence=evidence, comments=None, sort_order=ss_sort_order)
                s.add(add_constant)
                s.commit()

                check = s.query(SectionSortOrder).filter(SectionSortOrder.c_id==c_id).filter(SectionSortOrder.section_id==s_id).count()
                if check > 0:
                    data = {"sort_order": 0}
                    s.query(SectionSortOrder).filter(SectionSortOrder.c_id==c_id).filter(SectionSortOrder.section_id==s_id).update(data)
                    s.commit()
                else:
                    sort_order = SectionSortOrder(c_id=c_id,section_id=s_id,sort_order=0)
                    s.add(sort_order)
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
    #TODO does this just get custom subsections?
    """
    Fetches a list of subsections for a given competence
    :param c_id: id for the competence
    :param version: competence version
    """
    subsec_list = []

    subsecs = s.query(Subsection). \
        join(Section, Subsection.s_id_rel). \
        join(SectionSortOrder, Section.sort_order_rel). \
        join(Competence, SectionSortOrder.c_id_rel). \
        join(EvidenceTypeRef, Subsection.evidence_rel). \
        filter(Subsection.c_id == c_id). \
        filter(SectionSortOrder.c_id == c_id). \
        filter(Section.constant == 0). \
        filter(and_(Subsection.intro <= version,
                    or_(Subsection.last == None,
                        Subsection.last == version))). \
        order_by(asc(Subsection.sort_order)). \
        order_by(asc(SectionSortOrder.sort_order)). \
        values(Section.name.label('sec_name'),
               Subsection.name.label('subsec_name'),
               Subsection.comments, EvidenceTypeRef.type,
               SectionSortOrder.sort_order)

    sorted_result = sorted(list(subsecs),
                              key=lambda a: a.sort_order,
                              reverse=False)

    for sub in sorted_result:
        subsec_list.append(sub)

    return subsec_list


def get_constant_subsections(c_id, version):
    """
    Fetches a list of constant subsections for a given competency
    :param c_id: id for the competence
    :param version: competence version
    """
    constant_subsec_list = []
    constant_subsecs = s.query(Subsection). \
        join(Section, Subsection.s_id_rel). \
        join(SectionSortOrder, Section.sort_order_rel). \
        join(Competence, SectionSortOrder.c_id_rel). \
        join(EvidenceTypeRef, Subsection.evidence_rel). \
        filter(Subsection.c_id == c_id). \
        filter(Section.constant == 1). \
        filter(SectionSortOrder.c_id == c_id). \
        filter(and_(Subsection.intro <= version,
                    or_(Subsection.last == None,
                        Subsection.last == version))). \
        order_by(asc(Subsection.sort_order)). \
        order_by(asc(SectionSortOrder.sort_order)). \
        values(Section.name.label('sec_name'), Subsection.name.label('subsec_name'),
        Subsection.comments, EvidenceTypeRef.type,SectionSortOrder.sort_order, Subsection.c_id)

    sorted_result = sorted(list(constant_subsecs),
                           key=lambda a: a.sort_order,
                           reverse=False)

    for constant_sub in sorted_result:
        constant_subsec_list.append(constant_sub)

    return constant_subsec_list


@competence.route('/get_constant_subsections',methods=['GET', 'POST'])
@login_required
def get_constant_subsections_web():
    """
    Gets a list of constant subsections for web display
    """
    id = request.args["id"]
    result = []
    subsections = s.query(ConstantSubsections). \
        filter(ConstantSubsections.s_id==id). \
        all()
    for subsection in subsections:
        result.append({"name":subsection.item,"id":subsection.id})
    return jsonify({"response":result})


@competence.route('/activate_comp', methods=['GET', 'POST'])
@login_required
def activate_competency():
    """
    Activates a competency
    """
    c_id = request.json['c_id']
    s.query(Competence). \
        filter_by(id=c_id). \
        update({"current_version": 1})
    s.commit()
    return jsonify({"response":'Competence has been activated!'})


@competence.route('/section', methods=['GET', 'POST'])
@login_required
def get_section():
    #TODO check what this actually does
    """
    Gets subsections for a given section
    """
    if request.method == 'POST':
        # add subsection section database
        pass

    text = request.json['text']
    c_id = request.json['c_id']
    val = request.json['val']
    form = SectionForm()
    subsection_form = AddSubsection()

    # method below gets the subsections for the section_id selected in the form
    result_count = s.query(Subsection). \
        join(Competence). \
        join(Section). \
        join(EvidenceTypeRef). \
        filter(and_(Competence.id == c_id,
                    Section.id == val)). \
        count()

    if result_count != 0:
        result = s.query(Subsection). \
            join(Competence). \
            join(Section). \
            join(EvidenceTypeRef). \
            filter(and_(Competence.id == c_id,
                        Section.id == val)). \
            values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)

        table = ItemTableSubsections(result,
                                     classes=['table', 'table-striped', 'table-bordered', 'section_' + str(val)])
    else:
        table = '<table class="section_' + str(val) + '"></table>'

    # print str(c_id) + ' ' + str(val) + ' ' + 'should get subsections for selected section'
    return jsonify({"response":render_template('section.html', c_id=c_id, form=form, val=val, text=text, table=table,
                                   subsection_form=subsection_form)})


@competence.route('/delete_subsection', methods=['GET', 'POST'])
@login_required
def delete_subsection():
    """
    Deletes a subsection of a given competence
    """
    c_id = request.json['c_id']
    s_id = request.json['s_id']

    s.query(Subsection). \
        filter_by(c_id=request.json['c_id']). \
        filter_by(id=request.json["id"]). \
        delete()
    s.commit()

    result_count = s.query(Subsection). \
        join(Competence). \
        join(Section). \
        join(EvidenceTypeRef). \
        filter(and_(Competence.id == c_id, Section.id == s_id)).count()
    if result_count != 0:
        result = s.query(Subsection). \
            join(Competence). \
            join(Section). \
            join(EvidenceTypeRef). \
            filter(and_(Competence.id == c_id, Section.id == s_id)). \
            values(Subsection.id, Subsection.name, EvidenceTypeRef.type, Subsection.comments)

        table = ItemTableSubsections(result,
                                     classes=['table', 'table-striped', 'table-bordered', 'section_' + str(s_id)])
    else:
        table = '<table class="section_' + str(s_id) + '"></table>'

    return jsonify({"response":table})


@competence.route('/add_subsection_to_db', methods=['GET', 'POST'])
@login_required
def add_sections_to_db():
    #TODO check if this is just for custom subsections
    """
    Adds new custom subsection to the database
    """
    # method adds subsections to database
    # Gets information on existing subsections
    name = request.json['name']
    evidence_id = request.json['evidence_id']
    comments = request.json['comments']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    if "version" in request.json:
        version = request.json['version']
    else:
        version = 1

    # Quries current subsections, gets the max sort_order and increases by 1
    current_subsections = s.query(Subsection). \
        filter(Subsection.c_id == c_id). \
        all()
    print(f"current subsections: {current_subsections}")

    max=0
    for i in current_subsections:
        if i.sort_order is not None:
            if i.sort_order > max:
                max = i.sort_order
    new_sort_order = max+1

    # Creates a new subsection from data in form
    sub = Subsection(name=name, evidence=int(evidence_id), comments=comments, c_id=c_id, s_id=s_id,intro=version, sort_order=new_sort_order)
    s.add(sub)
    s.commit()
    sub_id = int(sub.id)

    #TODO what is this doing
    check = s.query(SectionSortOrder). \
        filter(SectionSortOrder.c_id == c_id). \
        filter(SectionSortOrder.section_id == s_id). \
        count()
    if check > 0:
        data = {"sort_order": 0}
        s.query(SectionSortOrder). \
            filter(SectionSortOrder.c_id == c_id). \
            filter(SectionSortOrder.section_id == s_id). \
            update(data)
        s.commit()
    else:
        sort_order = SectionSortOrder(c_id=c_id, section_id=s_id, sort_order=0)
        s.add(sort_order)
        s.commit()

    #TODO what is this doing
    result = s.query(Subsection). \
        join(Competence, Subsection.c_id_rel). \
        join(Section, Subsection.s_id_rel). \
        join(EvidenceTypeRef, Subsection.evidence_rel). \
        filter(Competence.id == c_id). \
        filter(Section.id == s_id). \
        values(Subsection.id, Subsection.name, EvidenceTypeRef.type, Subsection.comments)

    table = ItemTableSubsections(result, classes=['table', 'table-bordered', 'table-striped', 'section_' + str(s_id)])

    if "plain" in request.args:
        return jsonify({'id':sub_id})
    else:
        return jsonify({"response":table})


@competence.route('/add_constant_subsection_to_db', methods=['GET', 'POST'])
@login_required
def add_constant_sections_to_db():
    """
    Adds a new constant subsection to the database
    """
    name = request.json['name']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    version = request.json['version']
    if type(name) != str:
        name = name[0]
    else:
        name = name

    sub = Subsection(name=name, c_id=c_id, s_id=s_id, evidence=4, sort_order=None, comments=None, intro=version)
    s.add(sub)
    s.commit()

    sort_order = SectionSortOrder(c_id=c_id, section_id=s_id, sort_order=0)
    s.add(sort_order)
    s.commit()

    return jsonify({'id': sub.id})


@competence.route('/autocomplete_docs', methods=['GET'])
@login_required
def document_autocomplete():
    """
    Creates data for JS autocomplete of Q-Pulse docs
    """
    docs = s.query(Documents.qpulse_no). \
        distinct()
    doc_list = []
    for i in docs:
        doc_list.append(i.qpulse_no)

    return jsonify(json_list=doc_list)


@competence.route('/autocomplete_competence', methods=['GET'])
@login_required
def competence_name_autocomplete():
    """
    generates data for JS autocomplete of competence names
    """
    competencies = s.query(CompetenceDetails). \
        join(Competence). \
        filter(Competence.current_version == CompetenceDetails.intro). \
        all()
    competence_list = []
    for i in competencies:
        competence_list.append(i.category_rel.category + ": " + i.title)

    return jsonify(json_list=competence_list)


@competence.route('/get_docs', methods=['GET'])
@login_required
def get_documents(c_id):
    #TODO check what this is doing
    """

    """
    c_id = 1 #todo why is this set to 1??
    docid = request.json['add_document']
    documents = s.query(Documents). \
        join(Competence). \
        filter(competence.id == c_id)
    table = ItemTableDocuments(documents, classes=['table', 'table-striped', docid])
    return jsonify({"response":table})


@competence.route('/get_doc_name', methods=['POST', 'POST'])
@login_required
def get_doc_name(doc_id=None):
    """
    Get Q-Pulse document name
    """
    details = s.query(QPulseDetails). \
        first()
    q = QPulseWeb()
    if not doc_id:
        doc_id = request.json['doc_id']

        doc_name = q.get_doc_by_id(username=details.username, password=details.password, docNumber=doc_id)
        if doc_name == "False":
            return jsonify({"response":"This is not a valid QPulse Document"})
        else:
            return jsonify({"response":doc_name})

    else:
        doc_name = q.get_doc_by_id(username=details.username, password=details.password, docNumber=doc_id)
        return doc_name


@competence.route('/remove_doc', methods=['POST', 'POST'])
@login_required
def remove_doc():
    """
    Remove a document association from a competency
    """
    c_id = request.args["c_id"]
    doc_number = request.args["doc_number"]
    s.query(Documents). \
        filter(and_(Documents.c_id == c_id,
                    Documents.qpulse_no == doc_number)). \
        delete()
    s.commit()
    return jsonify({"success": True})


@competence.route('/add_doc', methods=['POST', 'POST'])
@login_required
def add_doc():
    """
    Add a Q-Pulse document record to a competency
    """
    c_id = request.args["c_id"]
    doc_number = request.args["doc_number"]

    if s.query(Documents). \
            filter(and_(Documents.c_id == c_id,
                        Documents.qpulse_no == doc_number)). \
            count() == 0:
        doc = Documents(c_id=c_id, qpulse_no=doc_number)
        s.add(doc)
        s.commit()
        return jsonify({"success": True})

# in jquery - if doc_name is not null, add doc name to list associated documents
# -if doc name is null, state "This is not an existing document in Qpulse"

@competence.route('/add_constant', methods=['GET', 'POST'])
@login_required
def add_constant_subsection():
    #TODO work out exactly what this is doing
    """
    Add a new constant subsection
    """
    s_id = request.json['s_id']
    item = request.json['item']
    add_constant = ConstantSubsections(s_id=s_id, item=item)
    s.add(add_constant)
    s.commit()
    return jsonify({"response":add_constant.id})


@competence.route('/view_competence', methods=['GET', 'POST'])
@login_required
def view_competence():
    """
    Fetch all information to view a given competency
    """
    c_id = request.args["c_id"]

    version = request.args["version"]

    get_comp_title = s.query(CompetenceDetails.title). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first()
    comp_title = ','.join(x for x in get_comp_title).replace("'", "")

    creator_id = s.query(CompetenceDetails.creator_id). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first(). \
        creator_id

    intro = s.query(CompetenceDetails.intro). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first(). \
        intro

    get_comp_scope = s.query(CompetenceDetails.scope). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first()
    comp_scope = ','.join(x for x in get_comp_scope).replace("'", "")

    get_comp_category = s.query(CompetenceCategory.category). \
        join(CompetenceDetails). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first()
    comp_category = ','.join(x for x in get_comp_category).replace("'", "")

    get_comp_val_period = s.query(ValidityRef.months). \
        join(CompetenceDetails). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first()
    comp_val_period = int(get_comp_val_period[0])

    approved = s.query(CompetenceDetails). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first(). \
        approved
    if approved == False:
        approver_id = s.query(CompetenceDetails). \
            filter_by(c_id=c_id). \
            filter(CompetenceDetails.intro == version). \
            first(). \
            approve_id
        if approver_id == current_user.database_id:
            approval_buttons = True
        else:
            approval_buttons = False
    else:
        approval_buttons = False
    if approved == None:
        c_detail_id = s.query(CompetenceDetails). \
            filter_by(c_id=c_id). \
            filter(CompetenceDetails.intro == version). \
            first(). \
            id
        feedback = s.query(CompetenceRejectionReasons). \
            filter(CompetenceRejectionReasons.c_detail_id == c_detail_id). \
            all()
    else:
        feedback = []

    id = s.query(CompetenceDetails). \
        filter_by(c_id=c_id). \
        filter(CompetenceDetails.intro == version). \
        first(). \
        id

    ##Creates a dictionary of the docs associated with a created competence
    dict_docs = {}
    if config.get("QPULSE_MODULE"):
        docs = s.query(Documents.qpulse_no). \
            join(CompetenceDetails). \
            filter(CompetenceDetails.intro == version). \
            filter_by(c_id=c_id)
        for doc in docs:
            #print(f"doc: {doc}")
            doc_id = ','.join(x for x in doc).replace("'", "")
            d = s.query(QPulseDetails). \
                first()
            #print(d)
            username = d.username
            password = d.password
            q = QPulseWeb()
            doc_name = q.get_doc_by_id(username=username, password=password, docNumber=doc_id)
            #print(f"doc name: {doc_name}")
            if doc_name == "False":
                doc_name = "There has been a problem locating this document in the Active register. " \
                           "Please contact the competence owner."
            # doc_active = q.check_doc_active(username=username, password=password, docNumber=doc_id)
            # if not doc_active:
            #     doc_name = "This document is no longer marked as active - please contact the competency owner."
            if doc_id is not "":
                dict_docs[doc_id] = doc_name
    #print(f"dict_docs: {dict_docs}")

    ##Get subsection details
    dict_subsecs = OrderedDict()
    subsections = get_subsections(c_id, version)
    for item in subsections:
        sec_name = item.sec_name
        subsection_name = item.subsec_name
        comment = item.comments
        evidence_type = item.type
        subsection_data = [subsection_name, comment, evidence_type]
        dict_subsecs.setdefault(sec_name, []).append(subsection_data)

    dict_constants = OrderedDict()
    constants = get_constant_subsections(c_id, version)
    for item in constants:
        constant_sec_name = item.sec_name
        constant_subsection_name = item.subsec_name
        constant_comment = item.comments
        constant_evidence_type = item.type
        constant_subsection_data = [constant_subsection_name, constant_comment, constant_evidence_type]
        dict_constants.setdefault(constant_sec_name, []).append(constant_subsection_data)

    return render_template('competence_view.html', intro=intro, creator_id=creator_id, c_id=c_id, title=comp_title, version=version, scope=comp_scope,
                           category=comp_category, val_period=comp_val_period, docs=dict_docs, constants=dict_constants,
                           subsections=dict_subsecs, review="yes", approved=approved, id=id, approval_buttons=approval_buttons, feedback=feedback)


@competence.route('/send_for_approval', methods=['GET'])
@login_required
def send_for_approval():
    """
    Send competence for approval
    """
    id = request.args["id"]
    s.query(CompetenceDetails). \
        filter(CompetenceDetails.id == id). \
        update({"approved": 0})
    s.commit()
    competence = s.query(CompetenceDetails). \
        filter(CompetenceDetails.id == id). \
        first()
    send_mail(competence.approve_id, "Competence awaiting your approval","You have a competence written by <b>" + current_user.full_name + "</b> to approve.")
    flash("Your competence has been sent for approval","success")
    return json.dumps({"success": True})


@competence.route('/force_approve')
@login_required
def force_authorise():
    #TODO should this be an admin thing?
    """
    Force authorisation of a competency
    """
    check = s.query(CompetenceDetails). \
        filter(CompetenceDetails.c_id == request.args["id"]). \
        first()
    if check.approved != 1:
        approve(id=request.args["id"],version=request.args["version"],u_id=current_user.database_id)
        flash("Competencies Force Authorised","success")
        return list_comptencies()
    else:
        flash("Competencies Already Authorised", "warning")
        return list_comptencies()


@competence.route('/expiry_dates')
@login_required
def expiry_dates():
    #TODO check exactly what this is doing
    """

    """
    form = ExpiryForm()
    return render_template("competence_expiry.html",form=form)


@competence.route('/matrix', methods=['GET'])
@login_required
def matrix():
    #TODO what is this doing??
    """

    """
    data = s.query(Subsection) \
        .join(Competence) \
        .join(CompetenceDetails)\
        .filter(CompetenceDetails.approved == 1). \
        all()

    users = s.query(Users). \
        filter(Users.active==True). \
        all()

    result = {}
    for i in data:
        title = i.c_id_rel.competence_detail[0].title
        if title not in result:
            result[title]={}
        if i.name not in result[title]:
            result[title][i.name]=[]
        for user in users:
            assessments = s.query(Assessments). \
                filter(Assessments.ss_id==i.id). \
                filter(Assessments.user_id==user.id). \
                all()
            details = {user:assessments}
            result[title][i.name].append(details)

    #contruct matrix here rather than in template
    #columns should be user
    #rows a subsection (grouped by competence?)
    #{ competence { subsection [user { status: x },user { status: x }] }
    return render_template("matrix.html", data=result,users=users)

@competence.route('/approve/<id>/<version>/<u_id>', methods=['GET'])
@login_required
def approve(id=None, version=None, u_id=None):
    """
    Approve a competency
    """
    user_allowed = s.query(CompetenceDetails). \
        filter(CompetenceDetails.c_id == id). \
        filter(CompetenceDetails.intro == version). \
        first(). \
        approve_id
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
        s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == id). \
            filter(CompetenceDetails.intro == version). \
            update(data)
        s.commit()

        # todo: should editing the details do this?
        # update competence details for last version
        data = {
            "last": int(version) - 1
        }
        s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == id). \
            filter(CompetenceDetails.intro == int(version) - 1). \
            update(data)
        s.commit()

        # update competence master table with current version
        data = {
            "current_version": version
        }
        s.query(Competence). \
            filter(Competence.id == id). \
            update(data)
        s.commit()

    else:
        print("User is not allowed to approve this competence")
        #TODO how does this render?

    competence = s.query(CompetenceDetails). \
        filter(CompetenceDetails.c_id == id). \
        filter(CompetenceDetails.intro == version). \
        first()
    send_mail(competence.creator_id, "Competence Approved!",
              "Your competence \""+competence.title+"\" has been approved by <b>" + current_user.full_name)

    return redirect('/')


@competence.route('/reject/<id>/<version>/<u_id>', methods=['GET','POST'])
@login_required
def reject(id=None, version=None, u_id=None):
    """
    Reject a competency
    """
    user_allowed = s.query(CompetenceDetails). \
        filter(CompetenceDetails.c_id == id). \
        filter(CompetenceDetails.intro == version). \
        first(). \
        approve_id
    if user_allowed == int(u_id):
        data = {
            "approve_id": u_id,
            "approved": None

        }

        competence = s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == id). \
            filter(CompetenceDetails.intro == version). \
            first()

        feedback = CompetenceRejectionReasons(c_detail_id=competence.id,date=datetime.date.today(),rejection_reason=request.form["feedback"])
        s.add(feedback)
        s.commit()

        s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == id). \
            filter(CompetenceDetails.intro == version). \
            update(data)
        s.commit()

        send_mail(competence.creator_id, "Competence Rejected!",
                  "Your competence \"" + competence.title + "\" has been rejected by <b>" + current_user.full_name)
        flash("Competence Rejected","danger")
        return redirect('/')


@competence.route('/check_exists', methods=['GET', 'POST'])
@login_required
def check_exists():
    """
    Check that a competence exists
    """
    if request.method == 'POST':
        if ":" in request.form["name"]:
            category, competence = request.form["name"].split(": ")
            c_query = s.query(Competence). \
                join(CompetenceDetails). \
                filter(CompetenceDetails.title == competence). \
                first()
            if c_query:
                return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@competence.route('/assign_user_to_competence', methods=['GET', 'POST'])
@login_required
def assign_user_to_competence():
    """
    Assign a user to a competence
    """
    ids = request.args["ids"].split(",")

    if request.method == 'POST':
        due_date = request.form["due_date"]
        category, competence = request.form["name"].split(": ")
        cat_id = s.query(CompetenceCategory). \
            filter_by(category=category). \
            first(). \
            id
        c_query = s.query(Competence). \
            join(CompetenceDetails). \
            filter(CompetenceDetails.title == competence). \
            filter(CompetenceDetails.category_id == cat_id). \
            first()
        c_id = c_query.id

        users = []
        for user_id in ids:
            assign_competence_to_user(int(user_id), int(c_id), due_date)
            user = s.query(Users). \
                filter(Users.id==user_id). \
                first()
            users.append(user.first_name + " " + user.last_name)

        flash("\"Competence "+ c_query.competence_detail[0].title +"\" assigned to "+",".join(users),"success")
        return redirect(url_for('competence.list_comptencies'))

    else:
        form = AssignForm()
        query = s.query(Users). \
            filter(Users.id.in_(ids)). \
            values(Users.first_name, Users.last_name)
        assignees = []
        for i in query:
            assignees.append(i.first_name + " " + i.last_name)

        return render_template('competence_assign.html', form=form, assignees=", ".join(assignees),
                               ids=request.args["ids"])


@competence.route('/assign_competences_to_user', methods=['GET', 'POST'])
@login_required
def assign_competences_to_user():
    """
    Assign competences to user
    """
    form = UserAssignForm()

    ids = request.args["ids"].split(",")

    if request.method == 'POST':
        users = request.form["user_list"].split(",")
        due_date = request.form["due_date"]
        result = {}
        for user in users:
            failed = []
            if user not in result:
                result[user] = []
            firstname, surname = user.split()
            count = s.query(Users). \
                filter_by(first_name=firstname, last_name=surname). \
                count()
            if count > 0:
                user_id = int(s.query(Users). \
                              filter_by(first_name=firstname, last_name=surname). \
                              first(). \
                              id)
                for c_id in ids:
                    final_id = assign_competence_to_user(user_id, int(c_id),due_date)

                    if final_id:
                        comp = s.query(Assessments). \
                            filter(Assessments.id.in_(final_id)). \
                            first()
                        current_version = s.query(Competence). \
                            filter(Competence.id == comp.ss_id_rel.c_id). \
                            first(). \
                            current_version
                        for i in comp.ss_id_rel.c_id_rel.competence_detail:
                            if i.intro == current_version:
                                result[user].append(dict(comptence=i.title, success=True))
            else:
                failed.append(user)
                failed.append(user)

        return render_template('competence_assigned.html', result=result, failed=failed)

    else:
        query = s.query(Competence). \
            join(CompetenceDetails, Competence.competence_detail). \
            filter(Competence.id.in_(ids)). \
            filter(Competence.current_version == CompetenceDetails.intro). \
            values(CompetenceDetails.title)
        comptences = []
        for i in query:
            comptences.append(i.title)

        return render_template('competence_user_assign.html', form=form, competences=", ".join(comptences),
                               ids=request.args["ids"])


@competence.route('/change_subsection_order', methods=['GET', 'POST'])
@login_required
def change_subsection_order():
    """
    Change the subsection order for a competency"""
    data = request.json
    for count,id in enumerate(data):
        new_order = {"sort_order":count}
        s.query(Subsection). \
            filter(Subsection.id == id). \
            update(new_order)
    s.commit()


@competence.route('/change_section_order', methods=['GET', 'POST'])
@login_required
def change_section_order():
    """
    Changes section order for a competency
    """
    data = request.json
    for c_id in data:
        for count,name in enumerate(data[c_id]):
            section_id = s.query(Section). \
                filter(Section.name == name). \
                first(). \
                id
            check = s.query(SectionSortOrder). \
                filter(SectionSortOrder.c_id==c_id). \
                filter(SectionSortOrder.section_id==section_id). \
                count()
            if check == 0:
                new = SectionSortOrder(c_id=c_id,section_id=section_id,sort_order=count)
                s.add(new)
            else:
                new_order = {"sort_order":count}
                s.query(SectionSortOrder). \
                    filter(SectionSortOrder.c_id == c_id). \
                    filter(SectionSortOrder.section_id==section_id). \
                    update(new_order)
    s.commit()


@competence.route('/make_user_competent', methods=['GET', 'POST'])
@admin_permission.require(http_exception=403)
def make_user_competent(ids=None,users=None):
    """
    Make a user competent
    """
    form = UserAssignForm()

    if ids == None:
        ids = request.args["ids"].split(",")
    if request.method == 'POST':
        if "due_date" in request.form:
            due_date = request.form["due_date"]
        else:
            due_date = datetime.date.today().strftime('%d/%m/%Y')
        expiry_date = request.form["expiry_date"]
        if users == None:
            users = request.form["user_list"].split(",")
        result = {}
        for user in users:
            failed = []
            if user not in result:
                result[user] = []
            firstname, surname = user.split()
            count = s.query(Users). \
                filter_by(first_name=firstname, last_name=surname). \
                count()
            if count > 0:
                user_id = int(s.query(Users). \
                              filter_by(first_name=firstname, last_name=surname). \
                              first(). \
                              id)
                for c_id in ids:
                    final_ids = assign_competence_to_user(user_id, int(c_id),due_date)
                    if final_ids is not None:
                        for ass_id in final_ids:
                            status_id = s.query(AssessmentStatusRef). \
                                filter(AssessmentStatusRef.status == "Complete"). \
                                first(). \
                                id
                            data = {'trainer_id': current_user.database_id,
                                    'date_of_training': datetime.date.today(),
                                    'date_completed': datetime.date.today(),
                                    'date_expiry': datetime.datetime.strptime(expiry_date, '%d/%m/%Y'),
                                    'date_activated': datetime.date.today(),
                                    'signoff_id': current_user.database_id,
                                    'status': status_id,
                                    }

                            s.query(Assessments). \
                                filter(Assessments.id == ass_id). \
                                update(data)
                            s.commit()

                        comp = s.query(Competence). \
                            join(CompetenceDetails). \
                            filter(Competence.id == int(c_id)). \
                            first()
                        result[user].append(dict(comptence=comp.competence_detail[0].title, success=True))
                    else:
                        return redirect(url_for('index'))
            else:
                failed.append(user)
                failed.append(user)
        if ids == None:
            return render_template('competence_assigned.html', result=result, failed=failed)
        else:
            return render_template('competence_assigned.html', result=result, failed=failed)
    else:
        query = s.query(Competence). \
            join(CompetenceDetails). \
            filter(Competence.id.in_(ids)). \
            values(CompetenceDetails.title)
        comptences = []
        for i in query:
            comptences.append(i.title)

        return render_template('competence_override.html', form=form, competences=", ".join(comptences),
                               ids=request.args["ids"])


def assign_competence_to_user(user_id, competence_id, due_date):
    #TODO check function
    #TODO does this need decorators?
    """
    Assign single competence to user
    """
    status_id = s.query(AssessmentStatusRef). \
        filter_by(status="Assigned"). \
        first(). \
        id
    # gets subsections for competence
    current_version = s.query(Competence). \
        filter(Competence.id == competence_id). \
        first(). \
        current_version
    sub_sections = s.query(Subsection). \
        filter(Subsection.c_id == competence_id). \
        filter(or_(Subsection.last == None,
                   Subsection.last == current_version)). \
        filter(Subsection.intro <= current_version). \
        all()

    sub_list = []

    # TODO Check if competence is already assigned, if it is skip user and display warning
    # TODO Need to add competence constant subsections

    for sub_section in sub_sections:
        sub_list.append(sub_section.id)

    check = s.query(Assessments). \
        join(AssessmentStatusRef). \
        filter(Assessments.ss_id.in_(sub_list)). \
        filter(Assessments.user_id==user_id). \
        filter(Assessments.version == current_version). \
        filter(or_(AssessmentStatusRef.status != "Obsolete",AssessmentStatusRef.status != "Abandoned")). \
        count()

    assessment_ids = []
    if check != 0:

        abandoned = s.query(Assessments).join(AssessmentStatusRef). \
            filter(Assessments.ss_id.in_(sub_list)). \
            filter(Assessments.user_id == user_id). \
            filter(Assessments.version == current_version). \
            filter(AssessmentStatusRef.status == "Abandoned"). \
            all()
        for assessment in abandoned:
            s.query(AssessmentEvidenceRelationship). \
                filter_by(assessment_id=assessment.id). \
                delete()
            s.query(Assessments). \
                filter_by(id=assessment.id). \
                delete()

    for sub_section in sub_sections:
        a = Assessments(status=status_id, ss_id=sub_section.id, user_id=int(user_id),
                        assign_id=current_user.database_id, version=current_version,
                        due_date=datetime.datetime.strptime(due_date, '%d/%m/%Y'))
        s.add(a)
        s.commit()
        assessment_ids.append(a.id)

    assigner = s.query(Users). \
        filter(Users.id == current_user.database_id). \
        first()
    try:
        send_mail(user_id, "Competence has been assigned to you",
                  "You have been assigned a competence by <b>" + assigner.first_name + " " + assigner.last_name + "</b>")
    except:
        s.rollback()

    return assessment_ids


@competence.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_competence():
    """
    Edit a competency
    """
    ids = request.args.get('ids').split(",")
    # todo: CHECK HERE IF COMPETENCE IS IN APPROVAL???
    c_id = ids[0]

    if current_user.database_id == s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == c_id). \
            first(). \
            creator_id or "ADMIN" in current_user.roles:

        form = EditCompetency()
        subsection_form = AddSubsection()
        section_form = AddSection()

        # get basic details for competence
        live = False
        current_version = s.query(Competence). \
            filter(Competence.id == c_id). \
            first(). \
            current_version
        if current_version:
            live = True

        comp_category = s.query(CompetenceCategory). \
            join(CompetenceDetails). \
            filter_by(c_id=c_id). \
            order_by(CompetenceDetails.intro.desc()). \
            first()
        form.edit_competency_type.choices = [(row.id, row.category) for row in (s.query(CompetenceCategory).values(CompetenceCategory.id,CompetenceCategory.category))]
        form.edit_competency_type.default = comp_category.id

        comp_val_period = s.query(ValidityRef). \
            join(CompetenceDetails).filter_by(c_id=c_id). \
            order_by(CompetenceDetails.intro.desc()). \
            first()

        form.edit_validity_period.choices = [(row.id, row.months) for row in (s.query(ValidityRef).values(ValidityRef.id, ValidityRef.months))]
        form.edit_validity_period.default = comp_val_period.id

        form.process()

        comp = s.query(CompetenceDetails).filter_by(c_id=c_id).order_by(CompetenceDetails.intro.desc()).first()
        form.edit_title.data = comp.title
        form.edit_scope.data = comp.scope

        form.approval.data = comp.approve_rel.first_name + " " + comp.approve_rel.last_name
        if config.get("QPULSE_MODULE"):
            doc_query = s.query(Documents.qpulse_no). \
                filter_by(c_id=comp.id). \
                all()
            documents = []
            for i in doc_query:
                name = get_doc_name(doc_id=i)
                if name != False:
                    documents.append([i.qpulse_no, name])
        else:
            documents = None
        # get subsections
        sub_result = OrderedDict()
        sub_result["constant"] = {}
        sub_result["custom"] = OrderedDict()

        for_order = s.query(SectionSortOrder). \
            filter(SectionSortOrder.c_id == c_id). \
            order_by(asc(SectionSortOrder.sort_order)). \
            all()
        for i in for_order:
            if i.section_id_rel.constant == 1:
                sub_result["constant"][(i.section_id_rel.name,i.section_id)]=[]
            else:
                sub_result["custom"][(i.section_id_rel.name, i.section_id)] = []

        subsections = s.query(Subsection). \
            filter(Subsection.c_id == c_id). \
            filter(Subsection.last == None). \
            order_by(asc(Subsection.c_id)). \
            order_by(asc(Subsection.sort_order)). \
            all()
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

        competence_copy = create_copy_of_competence(c_id, current_version, comp.title, comp.scope, comp_val_period.id,
                                              comp.category_id, comp.approve_id)

        return render_template('competence_edit.html', c_id=c_id, form=form, live=live, detail_id=competence_copy[0],subsections=sub_result, version=competence_copy[1], docs=json.dumps(documents),subsection_form=subsection_form,section_form=section_form)
    else:
        flash('You have to be an admin or the competence owner to edit the competence','danger')
        return redirect(url_for('competence.list_comptencies'))

def create_copy_of_competence(c_id, current_version, title, scope, valid, type, approve_id):
    """
    Create a copy of a competence, used when changing ownership
    """
    query = s.query(CompetenceDetails). \
        filter(CompetenceDetails.c_id == c_id). \
        filter(CompetenceDetails.intro == current_version + 1). \
        first()
    current = s.query(CompetenceDetails). \
        filter(CompetenceDetails.c_id == c_id). \
        filter(CompetenceDetails.intro == current_version). \
        first()
    if query is None:
        # make a copy of the competence
        c = CompetenceDetails(c_id=c_id, title=title, scope=scope, creator_id=current_user.database_id,
                              validity_period=valid, category_id=type, intro=current_version + 1,
                              approve_id=approve_id)
        s.add(c)
        s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == c_id). \
            filter(CompetenceDetails.intro == current_version). \
            update({"last": current_version})
        s.commit()

        # copy docs across to new competence
        current_docs = s.query(Documents). \
            filter(Documents.c_id == current.id). \
            all()
        for doc in current_docs:
            d = Documents(c_id=c.id, qpulse_no=doc.qpulse_no)
            s.add(d)
            s.commit()
        return (c.id,current_version+1)
    else:
        return (query.id,current_version+1)


@competence.route('/change_ownership', methods=['GET', 'POST'])
@login_required
def change_ownership():
    #TODO: should this only change ownership of the most recent version
    form = UserAssignForm()
    ids = request.args['ids']
    if request.method == 'POST':
        name = request.form["full_name"]
        firstname, surname = name.split(" ")
        new_creator_id = int(s.query(Users). \
                             filter_by(first_name=firstname, last_name=surname). \
                             first(). \
                             id)
        for id in ids.split(","):
            data = {"creator_id": new_creator_id}
            s.query(CompetenceDetails). \
                filter(CompetenceDetails.c_id == id). \
                update(data)

        try:
            s.commit()
            flash("Ownership changed to " + name,"success")
            return list_comptencies()
        except:
            flash("Something went wrong", "danger")
            return list_comptencies()

    return render_template('competence_change_ownership.html', form=form, ids=ids)


@competence.route('/edit_details', methods=['GET', 'POST'])
@login_required
def edit_details():
    c_id = request.args['c_id']
    title = request.form['edit_title']
    scope = request.form['edit_scope']
    firstname, surname = request.form['approval'].split(" ")
    valid = request.form['edit_validity_period']
    type = request.form['edit_competency_type']
    approve_id = int(s.query(Users). \
                     filter_by(first_name=firstname, last_name=surname). \
                     first(). \
                     id)
    data = {"title": title,
            "scope": scope,
            "approve_id": approve_id,
            "validity_period": valid,
            "category_id": type}

    current_version = int(s.query(Competence). \
                          filter(Competence.id == c_id). \
                          first(). \
                          current_version)
    # competence hasn't been made live yet - it's at version 0
    if current_version == 0:
        try:
            s.query(CompetenceDetails). \
                filter(CompetenceDetails.c_id == c_id). \
                update(data)
            s.commit()
            return json.dumps({"success": True})
        except:
            print ("fail")
    else:
        # check if a version exists above current version
        check = s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == c_id). \
            filter(CompetenceDetails.intro == current_version + 1). \
            count()
        if check == 0:
            # make a copy of the competence
            create_copy_of_competence(c_id, current_version, title, scope, valid, type, approve_id)

        s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == c_id). \
            filter(CompetenceDetails.intro == current_version + 1). \
            update(data)
        s.commit()
        return json.dumps({"success": True})


@competence.route('/delete', methods=['GET', 'POST'])
@login_required
def delete():
    """
    Deletes a competence in progress. If v>0, will only delete the newest version, leaving the live one
    """
    id = request.args.get('id') ### This is the CompetenceDetails ID
    c_id = s.query(CompetenceDetails). \
        filter(CompetenceDetails.id == id). \
        first(). \
        c_id ### this is the Competence id
    current_version = s.query(Competence). \
        filter(Competence.id == c_id). \
        first(). \
        current_version ### this is the Competence current version

    if current_version == 0:
        s.query(Documents). \
            filter(Documents.c_id == id). \
            delete() ### Delete associations to documents
        s.commit()
        s.query(CompetenceRejectionReasons). \
            filter(CompetenceRejectionReasons.c_detail_id == id). \
            delete() ### Delete any rejection reasons for that version
        s.commit()
        s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == c_id). \
            filter(CompetenceDetails.intro == current_version + 1). \
            delete() ### Delete the details for the in-progress competency
        s.commit()
        s.query(Subsection). \
            filter(Subsection.c_id == c_id). \
            filter(Subsection.intro == current_version + 1). \
            delete() ### Delete subsections for the in-progress competency
        s.commit()
        s.query(SectionSortOrder). \
            filter(SectionSortOrder.c_id == c_id). \
            delete() ### Delete the section order for the in-progress competency
        s.commit()
        s.query(Competence). \
            filter(Competence.id == c_id). \
            delete() ### Deletes the record for the competency as removing v0 removes competency
        s.commit()
        return json.dumps({'success': True})

    elif current_version >= 1:
        s.query(Documents). \
            filter(Documents.c_id == id). \
            delete() ### Deletes associated documents for that version only
        s.commit()
        s.query(CompetenceRejectionReasons). \
            filter(CompetenceRejectionReasons.c_detail_id == id). \
            delete() ### Deletes associated rejection reasons for that version only
        s.commit()
        s.query(CompetenceDetails). \
            filter(CompetenceDetails.c_id == c_id). \
            filter(CompetenceDetails.intro == current_version + 1). \
            delete() ### Deletes competence details for that version only
        s.commit()
        s.query(Subsection). \
            filter(Subsection.c_id == c_id). \
            filter(Subsection.intro == current_version + 1). \
            delete() ### Deletes subsections for that version only
        s.commit()
        return json.dumps({'success': True})

    else:
        print("Something failed here")
        return json.dumps({'success': False})


def nearest(items, pivot):
    #TODO what does this do
    """

    """
    return min(items, key=lambda x: abs(x - pivot))


def reporting():
    #TODO do we still need this now there's a new reports page?
    """

    """
    expired = {}
    expiring = {}
    overdue = {}
    activated_three_month = {}

    # get current
    services = s.query(Service).all()
    for i in services:
        service = i.name.replace(" ", "")

        expired[service] = {}
        expiring[service] = {}
        overdue[service] = {}
        activated_three_month[service] = {}

    for i in s.query(Assessments).all():
        if i.user_id_rel.service_rel is not None:
            if i.user_id_rel.active == 1:
                service = i.user_id_rel.service_rel.name.replace(" ", "")
                fullname = i.user_id_rel.first_name + " " + i.user_id_rel.last_name
                if i.date_expiry is not None:
                    comp_title = i.ss_id_rel.c_id_rel.competence_detail[0].title
                    if datetime.date.today() > i.date_expiry:
                        if fullname not in expired[service]:
                            expired[service][fullname] = {comp_title: i.date_expiry}
                        elif fullname in expired[service] and comp_title not in expired[service][fullname]:
                            expired[service][fullname][comp_title] = i.date_expiry
                        elif fullname in expired[service] and comp_title in expired[service][fullname]:
                            if i.date_expiry < expired[service][fullname][comp_title]:
                                expired[service][fullname][comp_title] = i.date_expiry


                    elif datetime.date.today() + relativedelta(months=+1) > i.date_expiry:
                        if fullname not in expiring[service]:
                            expiring[service][fullname] = {comp_title: i.date_expiry}
                        elif fullname in expiring[service] and comp_title not in expiring[service][fullname]:
                            expiring[service][fullname][comp_title] = i.date_expiry
                        elif fullname in expiring[service] and comp_title in expiring[service][fullname]:
                            if i.date_expiry < expiring[service][fullname][comp_title]:
                                expiring[service][fullname][comp_title] = i.date_expiry

                if i.status_rel.status in ["Active", "Assigned", "Failed", "Sign-Off"]:
                    if i.due_date < datetime.date.today():
                        comp_title = i.ss_id_rel.c_id_rel.competence_detail[0].title
                        if fullname not in overdue[service]:
                            overdue[service][fullname] = {comp_title: i.due_date}
                        elif fullname in overdue[service] and comp_title not in overdue[service][fullname]:
                            overdue[service][fullname][comp_title] = i.due_date

                if i.status_rel.status == "Active":
                    if datetime.date.today() + relativedelta(months=-3) > i.date_activated:
                        comp_title = i.ss_id_rel.c_id_rel.competence_detail[0].title
                        if fullname not in activated_three_month[service]:
                            activated_three_month[service][fullname] = {comp_title: i.due_date}
                        elif fullname in activated_three_month[service] and comp_title not in activated_three_month[service][fullname]:
                            activated_three_month[service][fullname][comp_title] = i.due_date


    return [expired,expiring, overdue, activated_three_month]


@competence.route('/report_by_section', methods=['GET', 'POST'])
@login_required
def report_by_section():
    """
    Generates graphs for monthly report by section
    """
    expired, expiring, overdue, activated_three_month = reporting()

    monthly_numbers = s.query(MonthlyReportNumbers).join(Service).order_by(desc(MonthlyReportNumbers.date))
    dates = []
    expired_dict = {}
    overdue_dict = {}
    completed_assessments_dict = {}
    completed_reassessments_dict = {}
    activated_dict = {}
    activated_three_month_dict = {}
    four_year_expiry_dict = {}

    colour_list=['rgb(2,16,176)', 'rgb(5,168,32)', 'rgb(5,179,232)']
    colour_dict={}
    for count, service in enumerate(s.query(Service).all()):
        colour_dict[service.name] = colour_list[count]

    for entry in monthly_numbers:
        if entry.date not in dates:
            dates.append(entry.date)

        service = str(entry.service_id_rel.name)
        if service not in expired_dict:
            expired_dict[service] = [int(entry.expired_assessments)]
            overdue_dict[service] = [int(entry.overdue_training)]
            completed_assessments_dict[service] = [int(entry.completed_assessments)]
            completed_reassessments_dict[service] = [int(entry.completed_reassessments)]
            activated_dict[service] = [int(entry.activated_assessments)]
            activated_three_month_dict[service] = [int(entry.activated_three_month_assessments)]
            four_year_expiry_dict[service] = [int(entry.four_year_expiry_assessments)]
        else:
            expired_dict[service].append(int(entry.expired_assessments))
            overdue_dict[service].append(int(entry.overdue_training))
            completed_assessments_dict[service].append(int(entry.completed_assessments))
            completed_reassessments_dict[service].append(int(entry.completed_reassessments))
            activated_dict[service].append(int(entry.activated_assessments))
            activated_three_month_dict[service].append(int(entry.activated_three_month_assessments))
            four_year_expiry_dict[service].append(int(entry.four_year_expiry_assessments))

    expired_fig = go.Figure()
    overdue_fig = go.Figure()
    completed_assessments_fig = go.Figure()
    completed_reassessments_fig = go.Figure()
    activated_assessments_fig = go.Figure()
    activated_assessments_three_month_fig = go.Figure()
    four_year_expiry_fig = go.Figure()

    ### assessments expired graph, left-side ###
    for service in expired_dict:
        expired_fig.add_trace(go.Scatter(x=dates, y=expired_dict[service], mode='lines+markers', name=service, line_color=colour_dict[service]))
    expired_fig.update_xaxes(dtick="M1", tickformat="%e %b\n%Y")
    expired_fig.update_layout(height=300, width=650, margin=dict(t=0, l=10, b=10, r=30), showlegend=False)
    expired_plot = plot(expired_fig, output_type="div")

    ### training overdue graph, right-side ###
    for service in overdue_dict:
        overdue_fig.add_trace(go.Scatter(x=dates, y=overdue_dict[service], mode='lines+markers', name=service, line_color=colour_dict[service]))
    overdue_fig.update_xaxes(dtick="M1", tickformat="%e %b\n%Y")
    overdue_fig.update_layout(height=300, width=800, margin=dict(t=0, l=50, b=10, r=0), showlegend=True)
    overdue_plot = plot(overdue_fig, output_type="div")

    ### completed assessments graph, left-side ###
    for service in completed_assessments_dict:
        completed_assessments_fig.add_trace(go.Scatter(x=dates, y=completed_assessments_dict[service], mode='lines+markers', name=service, line_color=colour_dict[service]))
    completed_assessments_fig.update_xaxes(dtick="M1", tickformat="%e %b\n%Y")
    completed_assessments_fig.update_layout(height=300, width=650, margin=dict(t=0, l=10, b=10, r=30), showlegend=False)
    completed_assessments_plot = plot(completed_assessments_fig, output_type="div")

    ### completed reassessments graph, right-side ###
    for service in completed_reassessments_dict:
        completed_reassessments_fig.add_trace(go.Scatter(x=dates, y=completed_reassessments_dict[service], mode='lines+markers', name=service, line_color=colour_dict[service]))
    completed_reassessments_fig.update_xaxes(dtick="M1", tickformat="%e %b\n%Y")
    completed_reassessments_fig.update_layout(height=300, width=800, margin=dict(t=0, l=50, b=10, r=0), showlegend=True)
    completed_reassessments_plot = plot(completed_reassessments_fig, output_type="div")

    ### activated assessments graph, left-sde ###
    for service in activated_dict:
        activated_assessments_fig.add_trace(go.Scatter(x=dates, y=activated_dict[service], mode='lines+markers', name=service, line_color=colour_dict[service]))
    activated_assessments_fig.update_xaxes(dtick="M1", tickformat="%e %b\n%Y")
    activated_assessments_fig.update_layout(height=300, width=650, margin=dict(t=0, l=10, b=10, r=30), showlegend=False)
    activated_assessments_plot = plot(activated_assessments_fig, output_type="div")

    ### activated threemonths ago graph, right-side ###
    for service in activated_three_month_dict:
        activated_assessments_three_month_fig.add_trace(go.Scatter(x=dates, y=activated_three_month_dict[service], mode='lines+markers', name=service, line_color=colour_dict[service]))
    activated_assessments_three_month_fig.update_xaxes(dtick="M1", tickformat="%e %b\n%Y")
    activated_assessments_three_month_fig.update_layout(height=300, width=800, margin=dict(t=0, l=50, b=10, r=0), showlegend=True)
    activated_assessments_three_month_plot = plot(activated_assessments_three_month_fig, output_type="div")

    ### four year expiry graph, left-side ###
    for service in four_year_expiry_dict:
        four_year_expiry_fig.add_trace(go.Scatter(x=dates, y=four_year_expiry_dict[service], mode='lines+markers', name=service, line_color=colour_dict[service]))
    four_year_expiry_fig.update_xaxes(dtick="M1", tickformat="%e %b\n%Y")
    four_year_expiry_fig.update_layout(height=300, width=800, margin=dict(t=0, l=10, b=10, r=30), showlegend=True)
    four_year_expiry_plot = plot(four_year_expiry_fig, output_type="div")

    return render_template('competence_report_by_section.html', expired=expired,
                           expiring=expiring, overdue=overdue, activated_three_month=activated_three_month,
                           expired_plot=Markup(expired_plot), overdue_plot=Markup(overdue_plot),
                           completed_assessments_plot=Markup(completed_assessments_plot),
                           completed_reassessments_plot=Markup(completed_reassessments_plot),
                           activated_assessments_plot=Markup(activated_assessments_plot),
                           activated_assessments_three_month_plot=Markup(activated_assessments_three_month_plot),
                           four_year_expiry_plot=Markup(four_year_expiry_plot))


@competence.route('/report_by_competence', methods=['GET', 'POST'])
@login_required
def report_by_competence():
    """
    Renders the reports by competence page
    """
    return render_template('competence_report_by_competence.html')

@competence.route('/report_by_user', methods=['GET', 'POST'])
@login_required
def report_by_user():
    """
    Loads the reports by user page, redirects to reports
    """
    if request.method == 'GET':
        return render_template('competence_report_by_user.html')
    elif request.method == "POST":
        user_full_name = request.form['full_name']
        first_name, surname = user_full_name.split(' ')
        user_id = s.query(Users).filter(and_(Users.first_name == first_name, Users.last_name == surname)).first().id
        return redirect(url_for('training.user_report', id=user_id))


@competence.route('/collections', methods=['GET', 'POST'])
@login_required
def collections():
    """
    Renders collections template
    08/21: this has been removed from the nav bar for now
    """
    return render_template('collections.html')

@competence.route('/trial_viewer', methods=['GET', 'POST'])
@login_required
def trial_viewer():
    """
    Renders the summary table for all competencies
    """
    ### get all current competencies ###
    current_data = s.query(CompetenceDetails). \
        join(Competence).filter(Competence.current_version == CompetenceDetails.intro). \
        all()
    result={}
    for comp in current_data: #loop through each competency, find out how many are trained, expired and partially and in training

        #count how many subsections are in the competence
        number_of_subsections = s.query(Subsection). \
            join(Competence). \
            filter(and_(Subsection.intro <= Competence.current_version,
                        or_(Subsection.last >= Competence.current_version,
                            Subsection.last == None))). \
            filter(Subsection.c_id == comp.c_id). \
            count()

        #get all assessments for this competence by user
        counts = s.query(func.count(Assessments.id).label("count"),
                         Assessments.user_id.label("user_id"),
                         Assessments.status.label("status_id"),
                         AssessmentStatusRef.status.label("status")). \
            join(AssessmentStatusRef). \
            join(Subsection). \
            join(Competence). \
            join(CompetenceDetails). \
            filter(and_(CompetenceDetails.intro <= Competence.current_version,
                         or_(CompetenceDetails.last >= Competence.current_version,
                             CompetenceDetails.last == None))). \
            filter(Subsection.c_id == comp.c_id). \
            filter(Assessments.ss_id == Subsection.id). \
            group_by(Assessments.user_id).all()

        trained=0
        partial=0
        in_training=0
        expired=0

        for user_entry in counts: ### loop through users that are on this competence
            if (s.query(Users). \
                    filter(Users.id == user_entry.user_id). \
                    first()). \
                    active == 1: ### check if user is actually active
                statuses = []

                ### get all assessments for this user for this competence, put statuses in list
                users_assessments = s.query(Assessments). \
                    join(Subsection). \
                    filter(Assessments.user_id == user_entry.user_id). \
                    filter(Subsection.c_id == comp.c_id). \
                    all()
                for entry in users_assessments:
                    if entry.status == 3: ### assessment is complete, check for expiry
                        if datetime.date.today() > entry.date_expiry:
                            statuses.append('Expired')
                        else:
                            statuses.append('Complete')
                    elif entry.status == 1 or entry.status == 7: ### assessment is active or waiting for sign-off
                        statuses.append('In training')

                ### from statuses list, decide on overall training status for this user for this competence, and add to counts
                if "In training" in statuses:
                    in_training += 1
                elif "Expired" in statuses:
                    expired+=1
                elif "Complete" in statuses:
                    if len(statuses) == int(number_of_subsections):
                        trained+=1
                    elif len(statuses) < int(number_of_subsections):
                        partial+=1

        result[comp.c_id]={"title":comp.title,
                        "trained":trained,
                        "expired":expired,
                        "partial":partial,
                        "training":in_training,
                        "category":comp.category_rel.category}


    return render_template('trial_viewer.html', current_data=current_data,result=result)


@competence.route('/history', methods=['GET', 'POST'])
@login_required
def competence_history():
    """
    Generates a change history for the competence
    """
    events = {}
    ids = request.args.get('ids').split(",")
    c_id = ids[0]
    competence = s.query(Competence). \
        filter(Competence.id == c_id). \
        first()
    version = competence.current_version
    title = {}

    for count, i in enumerate(competence.competence_detail):
        if i.date_of_approval is not None:
            if i.date_of_approval not in events:
                events[i.date_of_approval] = []
            events[i.date_of_approval].append(["Release", "<b>Version " + str(
                i.intro) + " was released!</b> Approved by " + i.approve_rel.first_name + " " + i.approve_rel.last_name,
                                               None])

        if i.date_created not in events:
            events[i.date_created] = []

        ss = []

        title["current"] = i.title

        if "previous" in title and "current" in title:
            if title["previous"] != title["current"]:
                ss.append('<h4>Title Edited</h4>')
                ss.append('<p class="text-green">+ ' + title["current"] + "</p>")
                ss.append('<p class="text-red">- ' + title["previous"] + "</p>")

        if i.intro > 1:
            subsections = s.query(Subsection). \
                filter(Subsection.c_id == c_id). \
                all()
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
    subsections = s.query(Subsection). \
        filter(Subsection.c_id == c_id). \
        filter(Subsection.last == version). \
        all()
    ss = []
    ss.append('<h4>Subsection(s) Edited</h4>')
    for j in subsections:
        ss.append('<p class="text-red">- ' + j.name + "</p>")

    ### why is this bit adding on an editing event today?
    # if datetime.date.today() not in events:
    #     events[datetime.date.today()] = []
    #
    # events[datetime.date.today()].insert(0, ["Edited",
    #                                          "<b>Edited by</b> " + i.creator_rel.first_name + " " + i.creator_rel.last_name,
    #                                          ss])

    return render_template('competence_history.html',
                           events=OrderedDict(sorted(events.items(), key=lambda t: t[0], reverse=True)))


@competence.route('/videos', methods=['GET', 'POST'])
@login_required
def videos():
    """
    Renders videos page
    """
    videos = s.query(Videos).all()
    return render_template("competence_videos.html",videos=videos)

@competence.route('/add_videos', methods=['GET', 'POST'])
@login_required
def add_videos():
    """
    Adds a new video
    """
    if request.method == 'POST':
        category, competence = request.form["name"].split(": ")
        cat_id = s.query(CompetenceCategory). \
            filter_by(category=category). \
            first(). \
            id
        c_query = s.query(CompetenceDetails). \
            join(Competence). \
            filter(CompetenceDetails.title == competence). \
            filter(CompetenceDetails.category_id == cat_id). \
            filter(and_(CompetenceDetails.intro <= Competence.current_version,
                        or_(CompetenceDetails.last >= Competence.current_version,
                            CompetenceDetails.last == None))). \
            first()
        video = Videos(date=datetime.date.today(),c_id=c_query.id,title=request.form['title'],embed_code=request.form['code'])
        s.add(video)
        s.commit()
        return redirect(url_for('competence.videos'))
    elif request.method == 'GET':
        return render_template("competence_video_add.html")


@competence.route('/remove_video/<id>', methods=['GET', 'POST'])
@login_required
def remove_video(id=None):
    """
    Remove a video from the database (admin only)
    """
    if 'ADMIN' in current_user.roles:
        s.query(Videos). \
            filter(Videos.id==id). \
            delete()
        s.commit()

    return videos()
