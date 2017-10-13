from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField
from wtforms.validators import Required

from app.competence import s
from app.models import *


class UserRoleForm(Form):
    role = TextField("Role",  [Required("Enter a Username")])
    submit = SubmitField("Add Role")
