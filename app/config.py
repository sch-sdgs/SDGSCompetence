
import os
basedir = os.path.dirname(os.path.dirname(__file__))


SQLALCHEMY_DATABASE_URI = 'mysql://stardb:stardb@10.182.155.30:92/stardb_dev'
SQLALCHEMY_TRACK_MODIFICATIONS = True
WHOOSH_BASE = os.path.join(basedir + '/app/resources/')