from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import SubmitField, TextAreaField, DateField, StringField

from app.competence import s
from app.models import *

class AddEvent(FlaskForm):
    """
    Form to add CPD event
    """
    event_name = StringField("Name")
    event_type = QuerySelectField("Type", query_factory=lambda: s.query(EventTypeRef).all(), get_label="type",allow_blank=True, blank_text="---Please Choose---")
    #event_type = QuerySelectField("Validity Period", query_factory=lambda: s.query(ValidityRef).all(), get_label="months")
    date = DateField('Date',
                     format='%Y-%m-%d', default=datetime.date.today)
    role = QuerySelectField("Participation", query_factory=lambda: s.query(EventRoleRef).all(), get_label="role", allow_blank=True, blank_text="---Please Choose---")
    #role = QuerySelectField("Validity Period", query_factory=lambda:s.query(ValidityRef).all(), get_label="months")
    location = StringField("Location")
    cpd_points = StringField("CPD points (if known)")
    comments = TextAreaField("Description/Comments")
    submit = SubmitField()