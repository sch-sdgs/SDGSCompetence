
import os
basedir = os.path.dirname(os.path.dirname(__file__))

SQLALCHEMY_DATABASE_URI = 'mysql://stardb:stardb@10.182.155.30:92/stardb_dev'

SQLALCHEMY_TRACK_MODIFICATIONS = True
WHOOSH_BASE = os.path.join(basedir + '/app/resources/')
UPLOAD_FOLDER = os.path.join('/uploads')
UPLOADED_FILES_DEST = os.path.join('/uploads')
QPULSE_MODULE=True
MAIL=True

MAIL_SERVER = 'smtp.sch.nhs.uk'
MAIL_PORT = 25
MAIL_USERNAME = None
MAIL_PASSWORD = None

# MAIL_SERVER = 'competencedb.com'
# MAIL_PORT = 2525
# MAIL_USERNAME = None
# MAIL_PASSWORD = None

ORGANISATION = "Sheffield Diagnostic Genetics Service"
ACTIVE_DIRECTORY = True

TRELLO_APP_KEY = '552b7506965909b0d129018876f692d3'
