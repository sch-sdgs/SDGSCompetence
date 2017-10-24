
import os
basedir = os.path.dirname(os.path.dirname(__file__))


SQLALCHEMY_DATABASE_URI = 'mysql://stardb:stardb@10.182.155.30:92/stardb_dev'
SQLALCHEMY_TRACK_MODIFICATIONS = True
WHOOSH_BASE = os.path.join(basedir + '/app/resources/')
UPLOAD_FOLDER = os.path.join(basedir + '/app/static/uploads')
UPLOADED_FILES_DEST = os.path.join(basedir + '/app/static/uploads')
print UPLOAD_FOLDER