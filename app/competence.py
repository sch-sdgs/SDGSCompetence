from flask import Flask, request,session, render_template
import atexit

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
from dateutil.relativedelta import relativedelta
import json

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
