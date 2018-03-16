from flask_wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField, SelectField, TextAreaField, SelectMultipleField
from wtforms.validators import Required

from app.competence import s
from app.models import *
from sqlalchemy.sql.functions import concat

class SectionForm(Form):
    subsection_name = TextField("Name")
    subsection_evidencetype = QuerySelectField("Evidence Type", query_factory=lambda: s.query(EvidenceTypeRef).all(),
                                               get_label="type")  # This belongs to a subsection
    subsection_comments = TextAreaField("Comment")


class AddCompetence(Form):
    title = TextField("Title", [Required("Enter a Title")])
    scope = TextField("Scope", [Required("Enter a Scope")])
    #qpulsenum = TextField("QPulse Doc ID", [Required("Enter a QPulse ID")]) #This needs to be added after competency creation!
    creator_id = TextField("Author Name", [Required("Enter an Author Name")])
    validity_period = QuerySelectField("Validity Period", query_factory=lambda:s.query(ValidityRef).all(), get_label="months")
    competency_type= QuerySelectField("Competence Category", query_factory=lambda:s.query(CompetenceCategory).all(), get_label="category")
    documents = QuerySelectMultipleField("Associated Documents",query_factory=lambda:s.query(Documents).all(), get_label="qpulse_no")
    add_document = TextField("Add Related Document", [Required("Enter a Q-Pulse Document Number")])
    submit = SubmitField()

class AddSection(Form):
    add_h_and_s = TextField("Add Health and Safety Hazard")
    choose_section = QuerySelectField("Add Section" ,query_factory=lambda:s.query(Section).filter(Section.constant == 0).all(), get_label="name") #All sections in database
    competence_sections = QuerySelectField("Add Section" ,query_factory=lambda:s.query(Section).all(), get_label="name") #All sections that are added for that specific competency
    submit = SubmitField()
    constant_section=QuerySelectMultipleField("Test")
    add_constant_subsection = TextField("Add new item")

class AddSubsection(Form):
    name = TextField("Area of Competence")
    evidence = QuerySelectField("Evidence type", query_factory=lambda:s.query(EvidenceTypeRef).all(), get_label="type")
    comments =TextField("Comments")


class AssignForm(Form):
    name = TextField("Area of Competence")
    submit = SubmitField()

class UserAssignForm(Form):
    full_name = TextField("Username")
    submit = SubmitField()

class EditCompetency(Form):
    #test_id=c_id
    edit_title = TextField("Title")
    edit_scope = TextField("Scope")
    # qpulsenum = TextField("QPulse Doc ID", [Required("Enter a QPulse ID")]) #This needs to be added after competency creation!
    edit_validity_period = QuerySelectField("Validity Period", query_factory=lambda: s.query(ValidityRef).all(),
                                       get_label="months")
    test_id=21
    edit_competency_type = QuerySelectField("Competence Category", query_factory=lambda: s.query(CompetenceCategory).all(),
                                       get_label="category")

    ass_documents=QuerySelectMultipleField("Associated Documents",  query_factory=lambda:s.query(Documents).filter_by(c_id=18).all(), get_label="qpulse_no")
    add_document = TextField("Add Related Document", [Required("Enter a Q-Pulse Document Number")])


