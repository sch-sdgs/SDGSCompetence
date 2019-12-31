from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField, SelectField, TextAreaField, SelectMultipleField, FileField, DateField
from wtforms.validators import Required

from app.competence import s
from app.models import *

class AddEvent(Form):
    """
    Form to add CPD event
    """
    event_name = TextAreaField(label="Name")
    event_type = QuerySelectField("Type",allow_blank=True, blank_text=u'-- please choose --',
                                      query_factory=lambda: s.query(EventTypeRef).all(),
                                      get_label="type")  # All sections in database
    date = DateField('Date',
                     format='%Y-%m-%d', default=datetime.date.today)
    role = SelectField(label="Participation",allow_blank=True, blank_text=u'-- please choose --',
                                      query_factory=lambda: s.query(EventRoleRef).all(),
                                      get_label="role")
    location = TextAreaField(label="Location")
    comments = TextAreaField(label="Comments")
