from app.mod_cpd.forms import *
from flask import render_template, redirect, request, url_for, Blueprint
from flask_login import current_user


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