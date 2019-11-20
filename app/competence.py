from flask import Flask, request,session, render_template
import atexit
from apscheduler.scheduler import Scheduler
import logging
from logging.handlers import TimedRotatingFileHandler
import inspect
import itertools
import time
from functools import wraps
from flask_login import current_user
import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.sql.expression import and_
from threading import Thread

app = Flask(__name__)
app.secret_key = 'development key'

app.config.from_envvar('CONFIG',silent=False)
config = app.config
app.jinja_env.add_extension('jinja2.ext.do')

from models import db,Users,Assessments,Evidence,CompetenceDetails,AssessmentStatusRef

s = db.session

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

handler = TimedRotatingFileHandler('PerformanceSummary.log', when="d", interval=1, backupCount=30)
handler.setLevel(logging.INFO)

#set up cron to allow jobs for monthly reports and backups
cron = Scheduler(daemon=True)
cron.start()

from flask_mail import Mail,Message

mail = Mail()
mail.init_app(app)


def send_async_email(msg):
    print "in async mail!"
    with app.test_request_context():
        print "inside app thing!"
        mail.send(msg)

def send_mail(user_id,subject,message):

    if config.get("MAIL") != False:
        #recipient_user_name = s.query(Users).filter(Users.id == int(user_id)).first().login
        recipient_email = s.query(Users).filter(Users.id == int(user_id)).first().email
        print recipient_email
        print "SENDING EMAIL"
        print message
        msg = Message('CompetenceDB: '+subject, sender="notifications@competencedb.com", recipients=[recipient_email])
        msg.body = 'text body'
        msg.html = '<b>You have a notification on CompetenceDB:</b><br><br>'+message+'<br><br>View all your notifications <a href="'+request.url_root+'notifications">here</a>'
        thr = Thread(target=send_async_email, args=[msg])
        print thr
        thr.start()



def send_mail_unknown(email,subject,message):

    if config.get("MAIL") != False:
        print "SENDING EMAIL"
        print message
        msg = Message('CompetenceDB: '+subject, sender="notifications@competencedb.com", recipients=[email])
        msg.body = 'text body'
        msg.html = message
        thr = Thread(target=send_async_email, args=[msg])
        thr.start()


def message(f):
    """
    decorator that allows query methods to log their actions to a log file so that we can track users

    :param f:
    :return:
    """
    @wraps(f)
    def decorated_function(*args,**kwargs):
        method = f.__name__

        formatter = logging.Formatter('%(levelname)s|' + current_user.id + '|%(asctime)s|%(message)s')
        handler.setFormatter(formatter)
        app.logger.addHandler(handler)

        args_name = inspect.getargspec(f)[0]
        args_dict = dict(itertools.izip(args_name, args))

        del args_dict['s']
        app.logger.info(method + "|" + str(args_dict))
        return f(*args, **kwargs)
    return decorated_function

#import modules and and register blueprints

from mod_admin.views import admin
from mod_training.views import training
from mod_competence.views import competence,reporting
from mod_document.views import document

app.register_blueprint(admin,url_prefix='/admin')
app.register_blueprint(training,url_prefix='/training')
app.register_blueprint(competence,url_prefix='/competence')
app.register_blueprint(document, url_prefix='/document')

import re
from models import MonthlyReportNumbers, Service

def check_notifications(user_id):
    expired = s.query(Assessments).filter(Assessments.user_id == user_id)
    alerts = {}
    count = 0
    for i in expired:
        if i.date_expiry is not None:
            if datetime.date.today() > i.date_expiry:
                if "Assessments Expired" not in alerts:
                    alerts["Assessments Expired"] = 1
                    count += 1
                else:
                    alerts["Assessments Expired"] += 1
                    count += 1
            elif datetime.date.today() + relativedelta(months=+6) > i.date_expiry:
                if "Assessments Expiring" not in alerts:
                    alerts["Assessments Expiring"] = 1
                    count += 1
                else:
                    alerts["Assessments Expiring"] += 1
                    count += 1
    signoff = s.query(Evidence).filter(Evidence.signoff_id == user_id).filter(
        Evidence.is_correct == None).count()
    if signoff > 0:
        count += signoff
        alerts["Evidence Approval"] = signoff
    approval = s.query(CompetenceDetails).filter(
        and_(CompetenceDetails.approve_id == user_id, CompetenceDetails.approved != None,
             CompetenceDetails.approved != 1)).count()
    if approval > 0:
        count += approval
        alerts["Competence Approval"] = approval

    return [count,alerts]


#####
# cron jobs to do things like check for expiring competencies, check for 4 year reassessments
#####

@cron.interval_schedule(days=30)
def report_scheduler():
    """
    runs reporting method from mod_competence - adds numbers to monthly reports table
    """

    counts, expired, expiring, user_expired, user_expiring, change = reporting()
    for service in counts:
        db_service = re.sub(r"(\w)([A-Z])", r"\1 \2", service)
        service_id = s.query(Service).filter(Service.name == db_service).first().id
        m = MonthlyReportNumbers(service_id=service_id,date=datetime.date.today(),assigned=counts[service]["Assigned"],active=counts[service]["Active"],expiring=counts[service]["Expiring"],expired=counts[service]["Expired"])
        s.add(m)
    try:
        s.commit()
    except:
        print "error"

@cron.interval_schedule(days=7)
def expiry_emailer():
    """
    checks database for any notifications and sends a summary every week
    """
    users = s.query(Users).filter(Users.active==1)
    for user in users:
        count,alerts = check_notifications(user.id)
        if count > 0:
            lines=["<b>Outstanding notifications</b><br>"]
            for i in alerts:
                with app.test_request_context():
                    time.sleep(5)
                    send_mail(user.id, "You have outstanding notifications!", "<br>".join(lines))


@cron.interval_schedule(days=1)
def four_year_checker():
    """
    check assessments every day for 4 year expiry
    """

    #do 46 months to give 2 months warning
    four_years_ago = datetime.date.today() - relativedelta(months=46)

    assessments = s.query(Assessments).join(AssessmentStatusRef).filter(
        AssessmentStatusRef.status == "Complete").filter(Assessments.date_completed <= four_years_ago)


    done = []
    for assessment in assessments:

        #update assessment status to indicate that 4 year is now due (maybe set them all?)
        status = s.query(AssessmentStatusRef).filter(AssessmentStatusRef.status == "Four Year Due").first().id
        data = { "status": status }
        s.query(Assessments).filter(Assessments.id == assessment.id).update(data)

        #only send email once for that competency
        if str(assessment.user_id) + ":" + str(assessment.ss_id_rel.c_id) not in done:

            lines = [assessment.ss_id_rel.c_id_rel.competence_detail[0].title + " is due for a four year reassessment."]
            lines.append("You originally completed this competency on "+str(assessment.date_completed))
            lines.append("Please arrange a suitable time with your trainer to reassess you competence fully.")

            with app.test_request_context():
                time.sleep(5)
                send_mail(assessment.user_id ,"Four Year Competency Reassessment Required: "+ assessment.ss_id_rel.c_id_rel.competence_detail[0].title,"<br><br>".join(lines))

        done.append(str(assessment.user_id) + ":" + str(assessment.ss_id_rel.c_id))

    s.commit()


# Shutdown your cron thread if the web process is stopped
atexit.register(lambda: cron.shutdown(wait=False))