from collections import OrderedDict

from flask import Blueprint, jsonify
from flask_table import Table, Col
from sqlalchemy import and_, or_, case
from flask import render_template, request, url_for, redirect, Blueprint
from flask_login import login_required, current_user
from app.views import admin_permission
from app.models import *
from app.competence import s
from forms import *
import json

competence = Blueprint('competence', __name__, template_folder='templates')

class ItemTableSubsections(Table):
    name = Col('Area of Competence')
    type = Col('Evidence Type')
    comments = Col('Comments')

class ItemTableDocuments(Table):
    qpulseno = Col('QPulse ID')
    title = Col('QPulse Document Title')


@competence.route('/add', methods=['GET', 'POST'])
def add_competence():
    form = AddCompetence()
    if request.method == 'POST':
        title = request.form['title']
        scope = request.form['scope']
        val_period = request.form['validity_period']
        c = Competence(title=title, creator_id=current_user.database_id, scope=scope, validity_period=val_period)
        s.add(c)
        s.commit()
        c_id = c.id
        doclist = request.form['doc_list'].split(',')
        for doc in doclist:
            add_doc = Documents(c_id=c_id, qpulse_no=doc)
            s.add(add_doc)
        s.commit()
        add_section_form = AddSection()
        return render_template('competence_section.html', form=add_section_form, c_id=c_id)

    return render_template('competence_add.html', form=form)

@competence.route('/addsections', methods=['GET', 'POST'])
def add_sections():
    form = AddSection()
    return render_template('competence_section.html', form=form)

@competence.route('/section', methods=['GET', 'POST'])
def get_section():

    if request.method == 'POST':
        # add subsection section database
        pass
    text = request.json['text']
    val = request.json['val']
    c_id = request.json['c_id']

    form = SectionForm()
    subsection_form = AddSubsection()
    #method below gets the subsections for the section_id selected in the form
    result_count = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(
        and_(Competence.id == c_id, Section.id == val)).count()
    if result_count != 0:
        result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(and_(Competence.id==c_id, Section.id==val)).values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)

        table = ItemTableSubsections(result, classes=['table', 'table-striped', 'section_'+str(val)])
    else:
        table = '<table class="section_'+str(val)+'"></table>'

    print str(c_id) + ' ' + str(val) + ' ' + 'should get subsections for selected section'
    return jsonify(render_template('section.html',c_id=c_id, form=form, val=val, text=text, table=table, subsection_form=subsection_form))


@competence.route('/add_subsection_to_db', methods=['GET', 'POST'])
def add_sections_to_db():
    #method adds subsections to database
    name = request.json['name']
    evidence_id = request.json['evidence_id']
    comments = request.json['comments']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    sub = Subsection(name=name,evidence=int(evidence_id),comments=comments,c_id=c_id,s_id=s_id)
    print s.add(sub)
    print s.commit()
    result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(Competence.id == c_id).filter(Section.id == s_id). \
        values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)

    table = ItemTableSubsections(result, classes=['table', 'table-striped', 'section_'+str(s_id)])
    #print str(c_id) + ' ' + str(s_id) + ' ' + 'should add new subsection to selected section'
    return jsonify(table)

@competence.route('/get_constants',methods=['GET', 'POST'])
def get_constant_sections():
    #Method to get all subsections that have a constant flag in the database
    constant = s.query(Subsection).filter(Section.constant==1).values(Section.id, Section.name)


@competence.route('/autocomplete_docs',methods=['GET'])
def document_autocomplete():
 doc_id = request.args.get('add_document')

 docs = s.query(Documents.qpulse_no).all()
 doc_list = []
 for i in docs:
     doc_list.append(i.qpulse_no)

 return jsonify(json_list=doc_list)

@competence.route('/get_docs',methods=['GET'])
def get_documents(c_id):
     c_id=1
     docid = request.json['add_document']
     documents=s.query(Documents).join(Competence).filter(competence.id == c_id)
     table =  ItemTableDocuments(documents, classes=['table', 'table-striped', docid])
     return jsonify(table)





