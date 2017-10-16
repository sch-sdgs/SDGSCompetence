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
    return render_template('competence_add.html', form=form)

@competence.route('/addsections', methods=['GET', 'POST'])
def add_sections():
    form = AddSection()

    return render_template('competence_section.html', form=form)

@competence.route('/add_subsection_to_db', methods=['GET', 'POST'])
def add_sections_to_db():

    name = request.json['name']
    evidence_id = request.json['evidence_id']
    comments = request.json['comments']
    c_id = request.json['c_id']
    s_id = request.json['s_id']
    sub = Subsection(name=name,evidence=evidence_id,comments=comments,c_id=c_id,s_id=s_id)
    s.add(sub)
    s.commit()
    result = s.query(Subsection).join(Competence).join(Section).filter(
        and_(Competence.id == c_id, Section.id == s_id)).values(Subsection.name, EvidenceTypeRef.type,
                                                               Subsection.comments)

    table = ItemTableSubsections(result, classes=['table', 'table-striped', 'section'])
    return jsonify(table)



@competence.route('/section', methods=['GET', 'POST'])
def get_section():
    """


    :return:
    """
    if request.method == 'POST':
        # add subsection section database
        pass
    text = request.json['text']
    val = request.json['val']
    c_id = request.json['c_id']

    form = SectionForm()
    subsection_form = AddSubsection()
    result = s.query(Subsection).join(Competence).join(Section).filter(and_(Competence.id==c_id, Section.id==val)).values(Subsection.name, EvidenceTypeRef.type, Subsection.comments)
    table = ItemTableSubsections(result, classes=['table', 'table-striped', 'section'])
    return jsonify(render_template('section.html',c_id=c_id, form=form, val=val, text=text, table=table, subsection_form=subsection_form))
