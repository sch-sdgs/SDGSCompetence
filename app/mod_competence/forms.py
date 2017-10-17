from flask.ext.wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField, SelectField, TextAreaField, SelectMultipleField
from wtforms.validators import Required

from app.competence import s
from app.models import *


class SectionForm(Form):
    subsection_name = TextField("Name")
    subsection_evidencetype = QuerySelectField("Evidence Type", query_factory=lambda: s.query(EvidenceTypeRef).all(),
                                               get_label="type")  # This belongs to a subsection
    subsection_comments = TextAreaField("Comment")
    # add = SubmitField()


class AddCompetence(Form):
    title = TextField("Title", [Required("Enter a Title")])
    scope = TextField("Scope", [Required("Enter a Scope")])
    #qpulsenum = TextField("QPulse Doc ID", [Required("Enter a QPulse ID")]) #This needs to be added after competency creation!
    creator_id = TextField("Author Name", [Required("Enter an Author Name")])
    validity_period = QuerySelectField("Validity Period", query_factory=lambda:s.query(ValidityRef).all(), get_label="months")

    documents = QuerySelectMultipleField("Associated Documents",query_factory=lambda:s.query(Documents).all(), get_label="qpulse_no")
    add_document = TextField("Add Document", [Required("Enter a Q-Pulse Document Number")])

    submit = SubmitField()


class AddSection(Form):

    h_and_s = QuerySelectMultipleField("Relevant Health and Safety", query_factory=lambda:s.query(HealthSafetyRef).all(), get_label="question") #This needs to be then added as a (constant) subsection to the competence
    add_h_and_s = TextField("Add Health and Safety Hazard")
    coshh = QuerySelectMultipleField("Related COSHH", query_factory=lambda: s.query(CoshhRef).all(),get_label="coshhitem") #This needs to be then added as a (constant) subsection to the competence
    add_coshh = TextField("Add COSHH Item")
    reagent_handling = QuerySelectMultipleField("Relevant reagent handling and storage", query_factory=lambda: s.query(ReagentRef).all(), get_label="reagent") #This needs to be then added as a (constant) subsection to the competence
    add_reagent = TextField("Add Reagent Handling or Storage Item")

    choose_section = QuerySelectField("Add Section" ,query_factory=lambda:s.query(Section).all(), get_label="name") #All sections in database
    competence_sections = QuerySelectField("Add Section" ,query_factory=lambda:s.query(Section).all(), get_label="name") #All sections that are added for that specific competency
    submit = SubmitField()

class AddSubsection(Form):
    name = TextField("Area of Competence")
    evidence = QuerySelectField("Evidence type", query_factory=lambda:s.query(EvidenceTypeRef).all(), get_label="type")
    comments =TextField("Comments")
