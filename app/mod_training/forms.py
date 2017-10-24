from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField, SelectField, TextAreaField, SelectMultipleField
from wtforms.validators import Required

from app.competence import s
from app.models import *

class UploadEvidence(Form):
    """
    For to submit evidence for a competence
    """
    
