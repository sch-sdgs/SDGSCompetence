from flask_wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField
from wtforms.validators import Required

from app.competence import s
from app.models import *


class UserRoleForm(Form):
    role = TextField("Role",  [Required("Enter a Username")])
    submit = SubmitField()

class EvidenceTypeForm(Form):
    type=TextField("Evidence Type",  [Required("Enter an Evidence Type")])
    submit = SubmitField()

class SectionForm(Form):
    name=TextField("Section Name",  [Required("Enter a Section Name")])
    constant=BooleanField("Applicable to all competencies?")
    submit = SubmitField()

class ValidityPeriodForm(Form):
    months=TextField("Validity period (months)",  [Required("Enter a Duration in months")])
    submit = SubmitField()