from flask import Flask, request,session, render_template
#from flask_apscheduler import APScheduler
import logging
from logging.handlers import TimedRotatingFileHandler
import inspect
import itertools
from functools import wraps
from flask_login import current_user
from threading import Thread
from dateutil.relativedelta import relativedelta
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

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

# scheduler = APScheduler()
# scheduler.init_app(app)
# scheduler.start()



# @scheduler.task('cron', id="log_monthly_numbers", month="*", day='1')
# @scheduler.task('cron', id="log_monthly_numbers", month="*", day='*', hour=13, minute=50)
# def log_completed_assessments_and_reassessments():
#     print("executing cron job")
    # todays_date = datetime.date.today()
    #
    # counts = {
    #     'complete_assessments': {},
    #     'complete_reassessments': {},
    #     'expired_assessments': {},
    #     'overdue_training': {},
    #     'activated_assessments': {},
    #     'activated_three_months_ago': {},
    #     'four_year_expiry_assessments': {}
    # }
    #
    # ### initialise counts for services ###
    # services = s.query(Service).all()
    # for service in services:
    #     service_id = service.id
    #     for item in counts:
    #         counts[item][service_id] = 0
    #
    # complete_assessments = s.query(Assessments) \
    #         .join(Users, Assessments.user_id == Users.id)\
    #         .join(Subsection)\
    #         .join(Competence)\
    #         .join(CompetenceDetails)\
    #         .join(AssessmentStatusRef)\
    #         .filter(CompetenceDetails.intro == Competence.current_version) \
    #         .filter(Users.active == 1)\
    #         .all()
    #
    # for assessment in complete_assessments:
    #     service_id = assessment.user_id_rel.serviceid
    #
    #     if assessment.status_rel.status == "Complete" or assessment.status_rel.status == "Four Year Due":
    #         if todays_date + relativedelta(months=-1) < assessment.date_completed: ### assessment has been completed in past month
    #             counts['complete_assessments'][service_id] +=1
    #         if todays_date > assessment.date_expiry:
    #             counts['expired_assessments'][service_id] +=1
    #         if todays_date + relativedelta(months=-49) < assessment.date_completed < todays_date + relativedelta(months=-48):
    #             counts['four_year_expiry_assessments'][service_id]+=1
    #
    #     elif assessment.status_rel.status == "Active":
    #         if todays_date + relativedelta(months=-1) < assessment.date_activated: ### assessment has been activated in the past month
    #             counts['activated_assessments'][service_id] +=1
    #         if todays_date + relativedelta(months=-3) > assessment.date_activated: ###assessmented has been activated but not completed in 3 months
    #             counts['activated_three_months_ago'][service_id] +=1
    #
    #     elif assessment.status_rel.status in ["Active", "Assigned", "Failed", "Sign-Off"]:
    #         if todays_date > assessment.due_date:
    #             counts['overdue_training'][service_id] +=1
    #
    #
    #
    # complete_reassessments = s.query(AssessReassessRel) \
    #     .join(Reassessments) \
    #     .join(Assessments) \
    #     .join(Users, Assessments.user_id == Users.id) \
    #     .join(Subsection) \
    #     .join(Competence) \
    #     .join(CompetenceDetails) \
    #     .join(AssessmentStatusRef) \
    #     .filter(CompetenceDetails.intro == Competence.current_version) \
    #     .filter(AssessmentStatusRef.status.in_(["Complete", "Four Year Due"])) \
    #     .filter(Users.active == 1) \
    #     .filter(Reassessments.is_correct == 1) \
    #     .all()
    #
    # for reassessment in complete_reassessments:
    #     if todays_date + relativedelta(months=-1) < reassessment.reassess_rel.date_completed:
    #         service_id = reassessment.assess_rel.user_id_rel.serviceid
    #         counts['complete_reassessments'][service_id]+=1
    #
    # print(json.dumps(counts, indent=4))
    #
    # for service in services:
    #     service_id = service.id
    #     entry = MonthlyReportNumbers(service_id=service_id,
    #                                  expired_assessments=counts['expired_assessments'][service_id],
    #                                  completed_assessments=counts['complete_assessments'][service_id],
    #                                  completed_reassessments=counts['complete_reassessments'][service_id],
    #                                  overdue_training=counts['overdue_training'][service_id],
    #                                  activated_assessments=counts['activated_assessments'][service_id],
    #                                  activated_three_month_assessments=counts['activated_three_months_ago'][service_id],
    #                                  four_year_expiry_assessments=counts['four_year_expiry_assessments'][service_id])
    #     s.add(entry)
    #     s.commit()


# database = config.get('SQLALCHEMY_DATABASE_URI')
# print(database)
# scheduler = BackgroundScheduler(jobstores={'default': SQLAlchemyJobStore(url=database, tablename='job_store')})
# scheduler.start()
# scheduler.add_job(log_completed_assessments_and_reassessments, 'cron', hour=15, minute=10)



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
