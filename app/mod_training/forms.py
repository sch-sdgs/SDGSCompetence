from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import SubmitField, HiddenField, SelectField, TextAreaField, FileField, StringField
from wtforms.fields.html5 import DateField
from app.competence import s
from app.models import *

class UploadEvidence(FlaskForm):
    """
    For to submit evidence for a competence
    """
    file = FileField('Upload Evidence')
    evidence_type = QuerySelectField("What type of evidence do you want to send?",allow_blank=True, blank_text=u'-- please choose --',
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
    case = StringField(label="Case")
    result = StringField(label="Result")
    assid = HiddenField("AssesmentID")
    submit = SubmitField('Submit Evidence')

class MarkNotRequired(FlaskForm):
    """
    For requesting subsection(s) are made inactive
    """
    inactivation_reason = TextAreaField(label="Reason these subsections do not require completion:")
    assessor = SelectField(label="Who will authorise that this training is not required?")
    assid = HiddenField("AssessmentID")
    submit = SubmitField("Submit Request")

class Reassessment(FlaskForm):
    signoff_id=SelectField(label="Authoriser")

class SubSectionsForm(FlaskForm):
    ids=HiddenField()
    submit=SubmitField('Continue')

class UserAssignForm(FlaskForm):
    trainer = StringField("Trainer")
    assessor = StringField("Assessor")
    assid = HiddenField("AssesmentID")
    submit = SubmitField()

class SignOffForm(FlaskForm):
    trainer = SelectField(label="Trainer")
    date = DateField('Date Trained',
                   format='%Y-%m-%d', default=datetime.date.today)
    assessor = SelectField(label="Assessor")
    #TODO you can click submit multiple times which causes asignee to receive multiple emails
    submit = SubmitField()