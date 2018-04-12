from flask import Flask
import atexit
from apscheduler.scheduler import Scheduler
import logging
from logging.handlers import TimedRotatingFileHandler
import inspect
import itertools
from functools import wraps
from flask_login import current_user
import app.config as config
import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.sql.expression import and_

#define app and db session

app = Flask(__name__)
app.secret_key = 'development key'
app.config.from_object(config)

from models import db,Users,Assessments,Evidence,CompetenceDetails

print app.config

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

mail = Mail(app)

def send_mail(user_id,subject,message):
    recipient_user_name = s.query(Users).filter(Users.id == int(user_id)).first().login
    print "SENDING EMAIL"
    print message
    msg = Message('StarDB: '+subject, sender="SDGS-Bioinformatics@sch.nhs.uk", recipients=[recipient_user_name+"@sch.nhs.uk"])
    msg.body = 'text body'
    msg.html = '<b>You have a notification on StarDB:</b><br><br>'+message+'<br><br>View all your notifications <a href="http://stardb/notifications">here</a>'

    with app.app_context():
        mail.send(msg)

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
from models import MonthlyReportNumbers, Service
from app.views import notifications
import re

app.register_blueprint(admin,url_prefix='/admin')
app.register_blueprint(training,url_prefix='/training')
app.register_blueprint(competence,url_prefix='/competence')
app.register_blueprint(document, url_prefix='/document')


@cron.interval_schedule(days=30)
def report_scheduler():
    """
    runs reporting method from mod_competence
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
                lines.append(i+": "+str(alerts[i]))

            send_mail(user.id,"You have outstanding notifications!","<br>".join(lines))



# Shutdown your cron thread if the web process is stopped
atexit.register(lambda: cron.shutdown(wait=False))