from flask import Flask
import logging
from logging.handlers import TimedRotatingFileHandler
import inspect
import itertools
from functools import wraps
from flask_login import current_user
import app.config as config

#define app and db session

app = Flask(__name__)
app.secret_key = 'development key'
app.config.from_object(config)

from models import db

print app.config

s = db.session

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

handler = TimedRotatingFileHandler('PerformanceSummary.log', when="d", interval=1, backupCount=30)
handler.setLevel(logging.INFO)

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
from mod_competence.views import competence
from mod_document.views import document

app.register_blueprint(admin,url_prefix='/admin')
app.register_blueprint(training,url_prefix='/training')
app.register_blueprint(competence,url_prefix='/competence')
app.register_blueprint(document, url_prefix='/document')


