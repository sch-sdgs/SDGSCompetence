from flask import Flask, render_template, redirect, request, url_for, session, current_app, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_required, login_user, logout_user, LoginManager, UserMixin, \
    current_user
from activedirectory import UserAuthentication
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
    identity_changed, Permission, RoleNeed, UserNeed,identity_loaded
from competence import app


training = Blueprint('training', __name__, template_folder='templates')

