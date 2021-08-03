from flask_wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import SubmitField, HiddenField, BooleanField, SelectMultipleField, SelectField, TextAreaField,PasswordField, StringField
from wtforms.validators import Required

from app.competence import s
from app.models import *


class UserRoleForm(Form):
    role = StringField("Role",  [Required("Enter a Username")])
    submit = SubmitField("Add Role")

class UserForm(Form):
    username = StringField("User Name", [Required("Enter a Username")])
    firstname = StringField("First Name", [Required("Enter a Username")])
    surname = StringField("Surname", [Required("Enter a Username")])
    email = StringField("Email", [Required("Enter a Username")])
    staff_no = StringField("Staff Number", [Required("Enter a Username")])
    linemanager = StringField("Line Manager")
    jobrole = QuerySelectMultipleField("Job Role", query_factory=lambda: s.query(JobRoles).all(), get_label="job")
    userrole = QuerySelectMultipleField("User Role", query_factory=lambda: s.query(UserRolesRef).all(), get_label="role")
    section = QuerySelectField("Section", query_factory=lambda: s.query(Service).all(),
                                        get_label="name")
    submit = SubmitField()


class UserEditForm(Form):
    username = StringField("User Name", [Required("Enter a Username")])
    firstname = StringField("First Name", [Required("Enter a Username")])
    surname = StringField("Surname", [Required("Enter a Username")])
    email = StringField("Email", [Required("Enter a Username")])
    staff_no = StringField("Staff Number", [Required("Enter a Username")])
    linemanager = StringField("Line Manager")
    jobrole = SelectMultipleField("Job Role")
    userrole = SelectMultipleField("User Role")
    section = SelectField("Section")
    submit = SubmitField()

class EvidenceTypeForm(Form):
    type = StringField("Evidence Type",  [Required("Enter an Evidence Type")])
    submit = SubmitField()


class CompetenceCategoryForm(Form):
    category = StringField("Competence Type",  [Required("Enter an Evidence Type")])
    submit = SubmitField()


class SectionForm(Form):
    name=StringField("Section Name",  [Required("Enter a Section Name")])
    constant=BooleanField("Applicable to all competencies?")
    submit = SubmitField()

class ConstantSubSectionForm(Form):
    name=StringField("SubSection Name",  [Required("Enter a Subsection Name")])
    section=SelectField("Section")
    submit = SubmitField()


class ValidityPeriodForm(Form):
    months=StringField("Validity period (months)",  [Required("Enter a Duration in months")])
    submit = SubmitField()

class AssessmentStatusForm(Form):
    status=StringField("Assessment Status",  [Required("Enter an Assessment Status")])
    submit = SubmitField()

class ServiceForm(Form):
    name=StringField("Service",  [Required("Enter a service")])
    submit = SubmitField()

class JobRoleForm(Form):
    job=StringField("Job Role",  [Required("Enter a job role")])
    submit = SubmitField()

class QuestionsForm(Form):
    question = StringField("Reassessment Question", [Required("Enter a reassessment question")])
    choices=[("Free text", "Free text"),("Date","Date"), ("Yes/no","Yes/no"), ("Dropdown","Dropdown")]
    type = SelectField("Answer type", choices=choices)
    submit = SubmitField()

class DropDownForm(Form):
    choice=StringField("Dropdown Choice",  [Required("Enter an dropdown choice")])
    submit = SubmitField()

class SubSectionAutoComplete(Form):
    phrase = TextAreaField("Phrase(s)", [Required("Enter a phrase")])
    submit = SubmitField()

class QPulseDetailsForm(Form):
    username = StringField("Q-Pulse Username")
    password = PasswordField("Q-Pulse Password")
    password_reenter = PasswordField("Re-Enter Q-Pulse Password")
    submit = SubmitField("Update Details")

class ChangePassword(Form):
    old_password = PasswordField("Old Password")
    new_password = PasswordField("New Password")
    new_password_check = PasswordField("Re-Enter New Password")
    submit = SubmitField()

class ResetPassword(Form):
    email = StringField("Registered Email")
    new_password = PasswordField("New Password")
    new_password_check = PasswordField("Re-Enter New Password")
    submit = SubmitField()