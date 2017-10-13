from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField, SelectField, TextAreaField, SelectMultipleField
from wtforms.validators import Required

from app.competence import s
from app.models import *


class AddCompetence(Form):
    title = TextField("Title", [Required("Enter a Title")])
    scope = TextField("Scope", [Required("Enter a Scope")])
    #qpulsenum = TextField("QPulse Doc ID", [Required("Enter a QPulse ID")]) #This needs to be added after competency creation!
    creator_id = TextField("Author Name", [Required("Enter an Author Name")])

    val_periods = ['6 Months', '1 Year', '2 Years']
    validity_period = SelectField("Validity Period", u'Query', choices=[(f, f) for f in val_periods])

    sections = ['Health & Safety', 'COSHH', 'Reagent Handling', 'Section1', 'Section2']
    section = SelectField("Section" , u'Query', choices=[(f, f) for f in sections])

    subsection_name = TextField("Name")

    subsection_evidencetype = QuerySelectField("Evidence Type", query_factory= )
    subsection_comments = TextAreaField("Comment")
    submit = SubmitField()

    hs_items = ['Manual Handling', 'Display Screen Equipment']
    h_and_s = SelectMultipleField('Health & Safety', choices=hs_items, coerce=unicode, option_widget=None)




