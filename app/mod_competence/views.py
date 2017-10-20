from collections import OrderedDict

from flask import Blueprint, jsonify
from flask_table import Table, Col, ButtonCol
from sqlalchemy import and_, or_, case
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import get_competence_from_subsections
from app.models import *
from app.competence import s
from forms import *
import json
from app.qpulseweb import *
from app.qpulse_details import QpulseDetails



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
        return '<a href="#" class="remove btn btn-sm btn-danger" id="'+str(item.id)+'"><span class="glyphicon glyphicon-remove"></span></a>'

class ItemTableSubsections(Table):
    name = Col('Area of Competence')
    type = Col('Evidence Type')
    comments = Col('Comments')
    id = DeleteCol('Remove')

class ItemTableDocuments(Table):
    qpulseno = Col('QPulse ID')
    title = Col('QPulse Document Title')

@competence.route('/list', methods=['GET', 'POST'])
def list_comptencies():

    data = s.query(CompetenceDetails).join(Competence).filter(Competence.current_version==CompetenceDetails).all()
    print data
    return render_template('competences_list.html',data=data)

@competence.route('/add', methods=['GET', 'POST'])
def add_competence():
    form = AddCompetence()
    if request.method == 'POST':
        title = request.form['title']
        scope = request.form['scope']
        val_period = request.form['validity_period']
        comp_category=request.form['competency_type']
        com = Competence()
        s.add(com)
        s.commit()

        c = CompetenceDetails(com.id, title, scope, current_user.database_id, val_period, comp_category)
        s.add(c)
        s.commit()
        c_id = c.id
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
                result[section.name]={}
                result[section.name][str(section.id)]=[]
            subsections = s.query(ConstantSubsections).filter_by(s_id=section.id).all()
            result[section.name][str(section.id)].append(subsections)

       # print request.form(dir())
        #return render_template('competence_section.html', form=add_section_form, c_id=c_id, result=result)
        return render_template('competence_section.html', form=add_section_form, c_id=com.id, result=result)

    return render_template('competence_add.html', form=form)

@competence.route('/addsections', methods=['GET', 'POST'])
def add_sections():
    print "hello"

    f = request.form
    c_id = request.args.get('c_id')
    print f
    for key in f.keys():
        if "subsections" in key:
            for value in f.getlist(key):
                print key, ":", value
                s_id = key[0]
                item_add=s.query(ConstantSubsections.item).filter_by(id=value).all()
                evidence = s.query(EvidenceTypeRef.id).filter_by(type='Discussion').all()

                add_constant=Subsection(c_id=c_id, s_id=s_id, name=item_add, evidence=evidence, comments=None)
                s.add(add_constant)
                s.commit()
    return render_template('competence_view.html', c_id=c_id)


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
    #method below gets the subsections for the section_id selected in the form
    result_count = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        and_(Competence.id == c_id, Section.id == val)).count()
    if result_count != 0:
        result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(and_(Competence.id==c_id, Section.id==val)).values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)

        table = ItemTableSubsections(result, classes=['table', 'table-striped', 'table-bordered' ,'section_'+str(val)])
    else:
        table = '<table class="section_'+str(val)+'"></table>'

    #print str(c_id) + ' ' + str(val) + ' ' + 'should get subsections for selected section'
    return jsonify(render_template('section.html',c_id=c_id, form=form, val=val, text=text, table=table, subsection_form=subsection_form))

@competence.route('/delete_subsection', methods=['GET', 'POST'])
def delete_subsection():
    print request.json
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    s.query(Subsection).filter_by(c_id = request.json['c_id']).filter_by(id=request.json["id"]).delete()
    s.commit()
    result_count = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        and_(Competence.id == c_id, Section.id == s_id)).count()
    if result_count != 0:
        result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
            and_(Competence.id == c_id, Section.id == s_id)).values(Subsection.id, Subsection.name, EvidenceTypeRef.type,
                                                                   Subsection.comments)

        table = ItemTableSubsections(result, classes=['table', 'table-striped', 'table-bordered', 'section_' + str(s_id)])
    else:
        table = '<table class="section_' + str(s_id) + '"></table>'
    return jsonify(table)


@competence.route('/add_subsection_to_db', methods=['GET', 'POST'])
def add_sections_to_db():
    #method adds subsections to database
    name = request.json['name']
    evidence_id = request.json['evidence_id']
    comments = request.json['comments']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    sub = Subsection(name=name,evidence=int(evidence_id),comments=comments,c_id=c_id,s_id=s_id)
    s.add(sub)
    s.commit()
    result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(Competence.id == c_id).filter(Section.id == s_id). \
        values(Subsection.id, Subsection.name, EvidenceTypeRef.type, Subsection.comments)

    table = ItemTableSubsections(result, classes=['table', 'table-bordered', 'table-striped', 'section_'+str(s_id)])
    #print str(c_id) + ' ' + str(s_id) + ' ' + 'should add new subsection to selected section'
    return jsonify(table)


@competence.route('/autocomplete_docs',methods=['GET'])
def document_autocomplete():
    doc_id = request.args.get('add_document')

    docs = s.query(Documents.qpulse_no).all()
    doc_list = []
    for i in docs:
        doc_list.append(i.qpulse_no)

    return jsonify(json_list=doc_list)


@competence.route('/autocomplete_competence', methods=['GET'])
def competence_name_autocomplete():
    competencies = s.query(CompetenceDetails).all()
    competence_list = []
    for i in competencies:
        competence_list.append(i.category_rel.category + ": "+  i.title)

    return jsonify(json_list=competence_list)

@competence.route('/get_docs',methods=['GET'])
def get_documents(c_id):
     c_id=1
     docid = request.json['add_document']
     documents=s.query(Documents).join(Competence).filter(competence.id == c_id)
     table =  ItemTableDocuments(documents, classes=['table', 'table-striped', docid])
     return jsonify(table)

@competence.route('/get_doc_name',methods=['POST', 'POST'])
def get_doc_name():

    d = QpulseDetails()
    details = d.Details()
    username=str(details[1])
    password=str(details[0])

    doc_id = request.json['doc_id']
    q=QPulseWeb()
    doc_name=q.get_doc_by_id(username=username, password=password, docNumber=doc_id)
    print doc_name
    if doc_name == "False":
        return jsonify("This is not a valid QPulse Document")
    else:
        return jsonify(doc_name)

#in jquery - if doc_name is not null, add doc name to list associated documents
# -if doc name is null, state "This is not an existing document in Qpulse"

@competence.route('/add_constant',methods=['GET','POST'])
def add_constant_subsection():
    s_id=request.json['s_id']
    item=request.json['item']
    add_constant=ConstantSubsections(s_id=s_id, item=item)
    s.add(add_constant)
    s.commit()
    return jsonify(add_constant.id)




@competence.route('/view_competence',methods=['POST'])
def view_competence():
        print "this method is being called"
        c_id = request.args.get('c_id')
        print c_id



    # competence_info= s.query(Competence).join(Users).filter_by(Competence.id==c_id).all()
    # print competence_info
    # subsection_list = s.query(Subsection). \
    #     join(Section). \
    #     join(Competence). \
    #     join(Documents). \
    #     filter(Subsection.c_id == c_id). \
    #     values(Subsection.name, Subsection.comments, Documents.qpulse_no, Section.constant, Subsection.evidence)
    # for subsection in subsection_list:
    #     print subsection

@competence.route('/assign_user_to_competence', methods=['GET', 'POST'])
def assign_user_to_competence():
    form = AssignForm()

    ids = request.args["ids"].split(",")

    if request.method == 'POST':
        category,competence = request.form["name"].split(": ")
        cat_id = s.query(CompetenceCategory).filter_by(category=category).first().id
        c_query = s.query(Competence).join(CompetenceDetails).filter(CompetenceDetails.title==competence).filter(CompetenceDetails.category_id==cat_id).first()
        c_id = c_query.id

        for user_id in ids:
            assign_competence_to_user(int(user_id),int(c_id))

    else:
        query = s.query(Users).filter(Users.id.in_(ids)).values(Users.first_name,Users.last_name)
        assignees = []
        for i in query:
            assignees.append(i.first_name + " " + i.last_name)


        return render_template('competence_assign.html',form=form,assignees=", ".join(assignees),ids=request.args["ids"])



def assign_competence_to_user(user_id,competence_id):
    status_id = s.query(AssessmentStatusRef).filter_by(status="Assigned").first().id
    # TODO Not Working
    sub_sections = s.query(Subsection).filter_by(c_id=competence_id).all()
    sub_list = []
    print "hello"
    print sub_sections
    # TODO Check if competence is already assigned, if it is skip user and display warning
    # TODO Need to add competence constant subsections

    for sub_section in sub_sections:
        sub_list.append(sub_section.id)

    check = s.query(Assessments).filter(Assessments.ss_id.in_(sub_list)).filter_by(user_id=user_id).count()
    if check == 0:
        for sub_section in sub_sections:
            print sub_section
            a = Assessments(status=status_id, ss_id=sub_section.id, user_id=int(user_id), assign_id=current_user.database_id)
            s.add(a)
            s.commit()

    return competence_id

@competence.route('/competence_edit', methods=['GET', 'POST'])
def edit_competence():
    #c_id = request.args.get('c_id')
    test_id = '18'

    form=EditCompetency()
    #get basic details for competence



    comp_title=s.query(CompetenceDetails.title).filter_by(c_id=test_id).first()
    form.edit_title.data=comp_title[0]

    comp_scope=s.query(CompetenceDetails.scope).filter_by(c_id=test_id).first()
    form.edit_scope.data = comp_scope[0]
    comp_category=s.query(CompetenceCategory.category).join(CompetenceDetails).filter_by(c_id=test_id).first()
    #form.edit_competency_type.default = comp_category[0]
    comp_val_period=s.query(ValidityRef.months).join(CompetenceDetails).filter_by(c_id=test_id).first()
    form.edit_validity_period.data = comp_val_period[0]
    print comp_val_period[0]
    print comp_category[0]
    print comp_scope[0]
    print comp_title[0]
    # documents=s.query(Documents.qpulse_no).filter_by(c_id=test_id).all()
    # for i in documents:
    #     print i[0]
    #     form.ass_documents.data=i[0]


    return render_template('competence_edit.html', form=form)
