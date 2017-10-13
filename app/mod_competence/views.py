from collections import OrderedDict

from flask import Blueprint
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import admin_permission
from app.models import *
from app.competence import s
from forms import *

competence = Blueprint('competence', __name__, template_folder='templates')

@competence.route('/add', methods=['GET', 'POST'])
def add_competence():
    form = AddCompetence()
    return render_template('competence_add.html', form=form)