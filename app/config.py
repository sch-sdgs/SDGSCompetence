
import os
basedir = os.path.dirname(os.path.dirname(__file__))


SQLALCHEMY_DATABASE_URI = 'mysql://stardb:stardb@10.182.155.30:92/stardb_live'
SQLALCHEMY_TRACK_MODIFICATIONS = True
WHOOSH_BASE = os.path.join(basedir + '/app/resources/')
UPLOAD_FOLDER = os.path.join(basedir + '/app/static/uploads')
UPLOADED_FILES_DEST = os.path.join(basedir + '/app/static/uploads')

MAIL_SERVER = 'smtp.sch.nhs.uk'
MAIL_PORT = 25
MAIL_USERNAME = None
MAIL_PASSWORD = None

