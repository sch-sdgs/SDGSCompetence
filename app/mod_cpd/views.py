from app.mod_cpd.forms import *
import csv
import datetime
from flask import render_template, redirect, request, url_for, Blueprint, send_file
from flask_login import current_user
from io import BytesIO, StringIO

### Set up cpd blueprint
cpd = Blueprint('cpd', __name__, template_folder='templates')


def get_cpd_by_user(user_id):
    """
    Query to get CPD events for user
    :param user_id: ID of user in DB
    :return: event query
    """
    events = s.query(CPDEvents). \
        join(EventRoleRef). \
        join(EventTypeRef). \
        filter(CPDEvents.user_id == user_id). \
        order_by(CPDEvents.date.desc()). \
        all()
    return events


def get_name_by_user_id(user_id):
    """
    Query to get user name by user ID
    :param user_id: ID of user in DB
    :return: String of first name + last name
    """
    user = s.query(Users). \
        filter(Users.id == user_id). \
        first()
    return user.first_name+' '+user.last_name


def format_query_for_csv():
    """
    Generates lists of CPD events for output to csv
    """
    user_id = current_user.database_id
    cpd_events = get_cpd_by_user(user_id)
    out_data = []
    headers = ["Event", "Type", "Date", "Role", "Location", "CPD points", "Description or Comment"]
    out_data.append(headers)
    for event in cpd_events:
        event_data = [event.event_name, event.event_type_rel.type, event.date.strftime('%d-%m-%Y'),
                      event.event_role_rel.role, event.location, event.cpd_points, event.comments]
        out_data.append(event_data)
    return out_data


@cpd.route('/view_cpd', methods=['GET'])
def view_cpd():
    """
    This methods finds CPD events and details for the user, and renders the HTML, showing a table of CPD events.
    """

    user_id = current_user.database_id
    username = get_name_by_user_id(user_id)

    cpd_events = get_cpd_by_user(user_id)

    return render_template('cpd_view.html', cpd=cpd_events, user=username)


@cpd.route('/add_cpd', methods=['GET', 'POST'])
def add_cpd():
    """
    This method adds CPD events. Once a CPD event is added, it returns to the view page.
    :return:
    """
    if request.method == 'GET':
        form = AddEvent()

        return render_template('cpd_add.html', form=form)

    elif request.method == 'POST':
        event_name = request.form['event_name']
        event_type = request.form["event_type"]
        date = request.form['date']
        role = request.form['role']
        location = request.form['location']
        cpd_points = request.form['cpd_points']
        comments = request.form['comments']

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
    This module delete a specific CPD event, using the ID of the event. Then returns to the view page.
    :return:
    """

    id = request.args.get('id')
    user_id = current_user.database_id

    event = s.query(CPDEvents). \
        filter(CPDEvents.id == id). \
        first()
    if event.user_id == user_id:
        s.delete(event)
        s.commit()

    return redirect(url_for('cpd.view_cpd'))


@cpd.route('/edit_cpd/<id>', methods=['GET', 'POST'])
def edit_cpd(id=None):
    """
    This method edits a specific CPD event, then returns to the main page
    """

    if request.method == 'GET':
        form = EditEvent()
        event = s.query(CPDEvents). \
            filter(CPDEvents.id == id). \
            first()
        form.event_name.data = event.event_name
        form.event_type.data = event.event_type
        form.date.data = event.date
        form.role.data = event.event_role
        form.location.data = event.location
        form.cpd_points.data = event.cpd_points
        form.comments.data = event.comments

        return render_template('cpd_edit.html', id=id, form=form)

    elif request.method == 'POST':
        form_data = {'event_name': request.form['event_name'],
                    'event_type': request.form['event_type'],
                    'date': request.form['date'],
                    'event_role': request.form['role'],
                    'location': request.form['location'],
                    'cpd_points': request.form['cpd_points'],
                    'comments': request.form['comments']}
        s.query(CPDEvents). \
            filter_by(id=id). \
            update(form_data)
        s.commit()
        return redirect(url_for('cpd.view_cpd'))


@cpd.route('download_cpd_log')
def download_cpd_log():
    """
    Generates a csv file of all CPD events in-memory for download
    """
    user_id = current_user.database_id
    username = get_name_by_user_id(user_id)
    today = datetime.date.today().strftime('%d-%m-%Y')
    out_data = format_query_for_csv()

    ### Write csv to temporary file
    temp = StringIO()
    csv.writer(temp).writerows(out_data)
    temp.seek(0)

    ### Convert to BytesIO for download
    b = BytesIO()
    b.write(temp.getvalue().encode())
    b.seek(0)

    return send_file(b, attachment_filename=f"{username} CPD Log {today}.csv", as_attachment=True)
