from flask import Flask, render_template, redirect, request, url_for, session, current_app, Blueprint, \
    send_from_directory, jsonify, Markup
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
import pandas as pd
from plotly.offline import plot
import plotly.graph_objs as go
import datetime

cpd = Blueprint('cpd', __name__, template_folder='templates')

def get_cpd_by_user(user_id):
    events = s.query(CPDEvents).join(EventRoleRef).join(EventTypeRef).filter(CPDEvents.user_id == user_id).order_by(CPDEvents.date.desc()).all()
    return events


def get_name_by_user_id(user_id):
    user = s.query(Users).filter(Users.id == user_id).first()
    return user.first_name+' '+user.last_name


@cpd.route('/view_cpd', methods=['GET'])
def view_cpd():
    """
    This module lists CPD events and details for the user
    """

    print "Welcome to the CPD module"
    user_id = current_user.database_id
    username = get_name_by_user_id(user_id)

    cpd_events = get_cpd_by_user(user_id)

    return render_template('cpd_view.html', cpd=cpd_events, user=username)

@cpd.route('/add_cpd', methods=['GET', 'POST'])
def add_cpd():
    """
    This module adds CPD events
    :return:
    """
    if request.method == 'GET':
        print "Adding CPD event"
        form = AddEvent()

        return render_template('cpd_add.html', form=form)

    elif request.method == 'POST':
        print "adding to DB"
        event_name = request.form['event_name']
        event_type = request.form["event_type"]
        date = request.form['date']
        role = request.form['role']
        location = request.form['location']
        cpd_points = request.form['cpd_points']
        comments = request.form['comments']


        print ' '.join([event_name, event_type, date, role, location, comments, cpd_points])

        c = CPDEvents(user_id=current_user.database_id,
                      event_type=event_type,
                      date=date,
                      event_role=role,
                      comments=comments,
                      location=location,
                      event_name=event_name,
                      cpd_points=cpd_points)

        s.add(c)
        s.commit()

        return redirect(url_for('cpd.view_cpd'))

@cpd.route('/delete_cpd', methods=['GET', 'POST'])
def delete_cpd():
    """
    This module delete a specific CPD event
    :return:
    """

    print "deleting CPD"
    id = request.args.get('id')
    print id

    user_id = current_user.database_id

    event = s.query(CPDEvents).filter(CPDEvents.id == id).first()
    if event.user_id == user_id:
        s.delete(event)
        s.commit()

    return redirect(url_for('cpd.view_cpd'))