from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import SubmitField, SelectField, TextAreaField, DateField, StringField
from wtforms.validators import DataRequired
from app.competence import s
from app.models import *

class SectionForm(FlaskForm):
    subsection_name = StringField("Name")
    subsection_evidencetype = QuerySelectField("Evidence Type", query_factory=lambda: s.query(EvidenceTypeRef).all(),
                                               get_label="type")  # This belongs to a subsection
    subsection_comments = TextAreaField("Comment")


class AddCompetence(FlaskForm):
    title = StringField("Title", [DataRequired("Enter a Title")])
    scope = StringField("Scope", [DataRequired("Enter a Scope")])
    creator_id = StringField("Author Name", [DataRequired("Enter an Author Name")])
    validity_period = QuerySelectField("Validity Period", query_factory=lambda:s.query(ValidityRef).all(), get_label="months")
    competency_type= QuerySelectField("Competence Category", query_factory=lambda:s.query(CompetenceCategory).all(), get_label="category")
    approval = StringField("Authoriser")
    documents = QuerySelectMultipleField("Associated Documents",query_factory=lambda:s.query(Documents).all(), get_label="qpulse_no")
    add_document = StringField("Add Related Document", [DataRequired("Enter a Q-Pulse Document Number")])
    submit = SubmitField()


class AddSection(FlaskForm):
    add_h_and_s = StringField("Add Health and Safety Hazard")
    choose_section = QuerySelectField("Add Section" ,query_factory=lambda:s.query(Section).filter(Section.constant == 0).all(), get_label="name") #All sections in database
    choose_constant_section = QuerySelectField("Add Constant Section",
                                      query_factory=lambda: s.query(Section).filter(Section.constant == 1).all(),
                                      get_label="name")  # All sections in database
    competence_sections = QuerySelectField("Add Section" ,query_factory=lambda:s.query(Section).all(), get_label="name") #All sections that are added for that specific competency
    submit = SubmitField()
    constant_section=QuerySelectMultipleField("Test")
    add_constant_subsection = StringField("Add new item")


class AddSubsection(FlaskForm):
    name = StringField("Area of Competence")
    evidence = QuerySelectField("Evidence type", query_factory=lambda:s.query(EvidenceTypeRef).all(), get_label="type")
    comments =StringField("Comments")


class AssignForm(FlaskForm):
    name = StringField("Area of Competence")
    due_date = DateField('Due Date', format='%Y-%m-%d')
    submit = SubmitField()


class ExpiryForm(FlaskForm):
    full_name = StringField("Full Name")
    submit = SubmitField()


class UserAssignForm(FlaskForm):
    full_name = StringField("Full Name")
    due_date =  DateField('Due Date', format='%Y-%m-%d')
    expiry_date = DateField('Expiry Date', format='%Y-%m-%d')
    submit = SubmitField()


class EditCompetency(FlaskForm):
    edit_title = StringField("Title")
    edit_scope = StringField("Scope")
    approval = StringField("Authoriser")
    edit_validity_period = SelectField("Validity Period", coerce=int)
    edit_competency_type = SelectField("Competence Category", coerce=int)
    ass_documents = QuerySelectMultipleField("Associated Documents",  query_factory=lambda:s.query(Documents).filter_by(c_id=18).all(), get_label="qpulse_no")
    add_document = StringField("Add Related Document", [DataRequired("Enter a Q-Pulse Document Number")])


class ViewCompetency(FlaskForm):
    view_title = StringField("Title:")
    view_scope = StringField("Scope:")
    view_validity_period =StringField("Validity Period(Months):")
    view_competency_type = StringField("Competence Type:")
    view_ass_documents = StringField("Qpulse Document:")
