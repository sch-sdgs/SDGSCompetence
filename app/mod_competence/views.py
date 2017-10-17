from collections import OrderedDict

from flask import Blueprint, jsonify
from flask_table import Table, Col
from sqlalchemy import and_, or_, case
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
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

@competence.route('/add', methods=['GET', 'POST'])
def add_competence():
    form = AddCompetence()
    if request.method == 'POST':
        print current_user.database_id
        title = request.form['title']
        print title
        scope = request.form['scope']
        print scope
        val_period = request.form['validity_period']
        print val_period
        c = Competence(title=title, creator_id=current_user.database_id, scope=scope, validity_period=val_period)
        s.add(c)
        s.commit()
        c_id = c.id
        print c_id

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
    result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(and_(Competence.id==c_id, Section.id==val)).values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)
    table = ItemTableSubsections(result, classes=['table', 'table-striped', 'section_'+str(val)])
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
    sub = Subsection(name=name,evidence=evidence_id,comments=comments,c_id=c_id,s_id=s_id)
    s.add(sub)
    s.commit()
    result = s.query(Subsection).join(Competence).join(Section).join(EvidenceTypeRef).filter(Competence.id == c_id).filter(Section.id == s_id). \
        values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)

    table = ItemTableSubsections(result, classes=['table', 'table-striped', 'section_'+str(s_id)])
    print str(c_id) + ' ' + str(s_id) + ' ' + 'should add new subsection to selected section'
    return jsonify(table)

def get_constants():
    #Method to get all subsections that have a constant flag in the database
    pass