from flask import Flask, request,session, render_template
from flask_apscheduler import APScheduler
import logging
from logging.handlers import TimedRotatingFileHandler
import inspect
import itertools
from functools import wraps
from flask_login import current_user
from threading import Thread

app = Flask(__name__)
app.secret_key = 'development key'

app.config.from_envvar('CONFIG',silent=False)
config = app.config
app.jinja_env.add_extension('jinja2.ext.do')

from models import *

s = db.session

###########################
### EMAIL NOTIFICATIONS ###
###########################

from flask_mail import Mail,Message

mail = Mail()
mail.init_app(app)


def send_async_email(msg):
    with app.test_request_context():
        mail.send(msg)

def send_mail(user_id,subject,message):

    if config.get("MAIL") != False:
        #recipient_user_name = s.query(Users).filter(Users.id == int(user_id)).first().login
        recipient_email = s.query(Users).filter(Users.id == int(user_id)).first().email
        msg = Message('CompetenceDB: '+subject, sender="notifications@competencedb.com", recipients=[recipient_email])
        msg.body = 'text body'
        msg.html = '<b>You have a notification on CompetenceDB</b><br><br>'+message+'<br><br>View all your notifications <a href="'+request.url_root+'notifications">here</a>'
        thr = Thread(target=send_async_email, args=[msg])
        thr.start()



def send_mail_unknown(email,subject,message):

    if config.get("MAIL") != False:
        msg = Message('CompetenceDB: '+subject, sender="notifications@competencedb.com", recipients=[email])
        msg.body = 'text body'
        msg.html = message
        thr = Thread(target=send_async_email, args=[msg])
        thr.start()



##################################################
### import modules and and register blueprints ###
##################################################

from mod_admin.views import admin
from mod_training.views import training
from mod_competence.views import competence,reporting
from mod_document.views import document
from mod_cpd.views import cpd
from mod_hos.views import hos

app.register_blueprint(admin,url_prefix='/admin')
app.register_blueprint(training,url_prefix='/training')
app.register_blueprint(competence,url_prefix='/competence')
app.register_blueprint(document, url_prefix='/document')
app.register_blueprint(cpd, url_prefix='/cpd')
app.register_blueprint(hos,url_prefix='/hos')

######################
### Scheduled Jobs ###
######################

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# @scheduler.task('cron', id="log_monthly_numbers", hour=5, day_of_month=1)
# def log_completed_assessments_and_reassessments():
#
# def log_expired_competencies();
#
# def log_overdue_training():
#
# def log_activated_competencies():
#
# def log_four_year_expiry_competencies():

# def check_notifications(user_id):
#     print "CHECKING EXPIRED ASSESSMENTS"
#     expired = s.query(Assessments).filter(Assessments.user_id == user_id)
#     alerts = {}
#     count = 0
#     for i in expired:
#         if i.date_expiry is not None:
#             if datetime.date.today() > i.date_expiry:
#                 if "Assessments Expired" not in alerts:
#                     alerts["Assessments Expired"] = 1
#                     count += 1
#                 else:
#                     alerts["Assessments Expired"] += 1
#                     count += 1
#             elif datetime.date.today() + relativedelta(months=+1) > i.date_expiry:
#                 if "Assessments Expiring" not in alerts:
#                     alerts["Assessments Expiring"] = 1
#                     count += 1
#                 else:
#                     alerts["Assessments Expiring"] += 1
#                     count += 1
#     signoff = s.query(Evidence).filter(Evidence.signoff_id == user_id).filter(
#         Evidence.is_correct == None).count()
#     if signoff > 0:
#         count += signoff
#         alerts["Evidence Approval"] = signoff
#     approval = s.query(CompetenceDetails).filter(
#         and_(CompetenceDetails.approve_id == user_id, CompetenceDetails.approved != None,
#              CompetenceDetails.approved != 1)).count()
#     if approval > 0:
#         count += approval
#         alerts["Competence Approval"] = approval
#
#     return [count,alerts]
