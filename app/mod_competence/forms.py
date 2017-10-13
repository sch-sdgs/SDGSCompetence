from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
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
    validity_period = QuerySelectField("Validity Period", query_factory=lambda:s.query(ValidityRef).all(), get_label="months")
    documents = QuerySelectMultipleField("Associated Documents",query_factory=lambda:s.query(Documents).all(), get_label="qpulse_no")

    section = QuerySelectField("Add Section" ,query_factory=lambda:s.query(Section).all(), get_label="name")
    subsection_name = TextField("Name")
    subsection_evidencetype = QuerySelectField("Evidence Type", query_factory=lambda:s.query(EvidenceTypeRef).all(), get_label="type")
    subsection_comments = TextAreaField("Comment")
    submit = SubmitField()
    h_and_s = QuerySelectMultipleField("Relevant Health and Safety", query_factory=lambda:s.query(HealthSafetyRef).all(), get_label="question") #This needs to be then added as a (constant) subsection to the competence
    coshh = QuerySelectMultipleField("Related COSHH", query_factory=lambda: s.query(CoshhRef).all(),get_label="coshhitem") #This needs to be then added as a (constant) subsection to the competence
    reagent_handling = QuerySelectMultipleField("Relevant reagent handling and storage", query_factory=lambda: s.query(ReagentRef).all(), get_label="reagent") #This needs to be then added as a (constant) subsection to the competence






