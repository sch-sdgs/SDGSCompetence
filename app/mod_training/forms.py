from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField, SelectField, TextAreaField, SelectMultipleField, FileField, DateField
from wtforms.validators import Required

from app.competence import s
from app.models import *

class UploadEvidence(Form):
    """
    For to submit evidence for a competence
    """
    file = FileField('Upload Evidence')
    evidence_type = QuerySelectField("What type of evidence do you want to upload?",allow_blank=True, blank_text=u'-- please choose --',
                                      query_factory=lambda: s.query(EvidenceTypeRef).all(),
                                      get_label="type")  # All sections in database
    trainer = SelectField(label="Who was your trainer?")
    datecompleted = DateField('What date did you attain this evidence?',
                           format='%Y-%m-%d', default=datetime.date.today)
    datetrained = DateField('What date did you train?',
                     format='%Y-%m-%d', default=datetime.date.today)
    assessor = SelectField(label="Who will sign-off this evidence?")
    evidence_observation = TextAreaField(label="Evidence")
    evidence_discussion = TextAreaField(label="Evidence")
    case = TextField(label="Case")
    result = TextField(label="Result")
    assid = HiddenField("AssesmentID")
    submit = SubmitField('Submit Evidence')

class Reassessment(Form):
    signoff_id=SelectField(label="Authoriser")

class SubSectionsForm(Form):
    ids=HiddenField()
    submit=SubmitField('Continue')

class UserAssignForm(Form):
    trainer = TextField("Trainer")
    assessor = TextField("Assessor")
    assid = HiddenField("AssesmentID")
    submit = SubmitField()

class SignOffForm(Form):
    trainer = SelectField(label="Trainer")
    date = DateField('Date Trained',
                   format='%Y-%m-%d', default=datetime.date.today)
    assessor = SelectField(label="Assessor")
    submit = SubmitField()