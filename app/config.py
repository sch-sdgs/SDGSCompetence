
import os
basedir = os.path.dirname(os.path.dirname(__file__))


#SQLALCHEMY_DATABASE_URI = 'mysql://stardb:stardb@0.0.0.0:81/stardb_dev'
SQLALCHEMY_DATABASE_URI = 'mysql://stardb:stardb@10.182.155.30:92/stardb_live'
SQLALCHEMY_TRACK_MODIFICATIONS = True
WHOOSH_BASE = os.path.join(basedir + '/app/resources/')
UPLOAD_FOLDER = os.path.join('/uploads')
UPLOADED_FILES_DEST = os.path.join('/uploads')
#QPULSE_MODULE=False
QPULSE_MODULE=True

MAIL_SERVER = 'smtp.sch.nhs.uk'
MAIL_PORT = 25
MAIL_USERNAME = None
MAIL_PASSWORD = None
#
# MAIL_SERVER = 'smtp.mailtrap.io'
# MAIL_PORT = '2525'
# MAIL_USERNAME = "80753817cf5a63"
# MAIL_PASSWORD = "c69cbe5572dd88"

TRELLO_APP_KEY = '552b7506965909b0d129018876f692d3'
