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
    evidence = Col('Evidence Type')
    comments = Col('Comments')

@competence.route('/add', methods=['GET', 'POST'])
def add_competence():
    form = AddCompetence()
    return render_template('competence_add.html', form=form)

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
    result = s.query(Subsection).join(Competence).join(Section).filter(and_(Competence.id==c_id, Section.id==val)).values(Subsection.name, Subsection.evidence, Subsection.comments)
    table = ItemTableSubsections(result, classes=['table', 'table-striped'])
    return jsonify(render_template('section.html', form=form, val=val, text=text, table=table))
