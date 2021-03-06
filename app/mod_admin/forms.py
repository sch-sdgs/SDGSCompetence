from flask_wtf import Form
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import TextField, SubmitField, HiddenField, BooleanField, SelectMultipleField, SelectField, TextAreaField,PasswordField
from wtforms.validators import Required

from app.competence import s
from app.models import *


class UserRoleForm(Form):
    role = TextField("Role",  [Required("Enter a Username")])
    submit = SubmitField("Add Role")

class UserForm(Form):
    username = TextField("User Name", [Required("Enter a Username")])
    firstname = TextField("First Name", [Required("Enter a Username")])
    surname = TextField("Surname", [Required("Enter a Username")])
    email = TextField("Email", [Required("Enter a Username")])
    staff_no = TextField("Staff Number", [Required("Enter a Username")])
    linemanager = TextField("Line Manager")
    jobrole = QuerySelectMultipleField("Job Role", query_factory=lambda: s.query(JobRoles).all(), get_label="job")
    userrole = QuerySelectMultipleField("User Role", query_factory=lambda: s.query(UserRolesRef).all(), get_label="role")
    section = QuerySelectField("Section", query_factory=lambda: s.query(Service).all(),
                                        get_label="name")
    submit = SubmitField()


class UserEditForm(Form):
    username = TextField("User Name", [Required("Enter a Username")])
    firstname = TextField("First Name", [Required("Enter a Username")])
    surname = TextField("Surname", [Required("Enter a Username")])
    email = TextField("Email", [Required("Enter a Username")])
    staff_no = TextField("Staff Number", [Required("Enter a Username")])
    linemanager = TextField("Line Manager")
    jobrole = SelectMultipleField("Job Role")
    userrole = SelectMultipleField("User Role")
    section = SelectField("Section")
    submit = SubmitField()

class EvidenceTypeForm(Form):
    type=TextField("Evidence Type",  [Required("Enter an Evidence Type")])
    submit = SubmitField()


class CompetenceCategoryForm(Form):
    category=TextField("Competence Type",  [Required("Enter an Evidence Type")])
    submit = SubmitField()


class SectionForm(Form):
    name=TextField("Section Name",  [Required("Enter a Section Name")])
    constant=BooleanField("Applicable to all competencies?")
    submit = SubmitField()

class ConstantSubSectionForm(Form):
    name=TextField("SubSection Name",  [Required("Enter a Subsection Name")])
    section=SelectField("Section")
    submit = SubmitField()


class ValidityPeriodForm(Form):
    months=TextField("Validity period (months)",  [Required("Enter a Duration in months")])
    submit = SubmitField()

class AssessmentStatusForm(Form):
    status=TextField("Assessment Status",  [Required("Enter an Assessment Status")])
    submit = SubmitField()

class ServiceForm(Form):
    name=TextField("Service",  [Required("Enter a service")])
    submit = SubmitField()

class JobRoleForm(Form):
    job=TextField("Job Role",  [Required("Enter a job role")])
    submit = SubmitField()

class QuestionsForm(Form):
    question = TextField("Reassessment Question", [Required("Enter a reassessment question")])
    choices=[("Free text", "Free text"),("Date","Date"), ("Yes/no","Yes/no"), ("Dropdown","Dropdown")]
    type = SelectField("Answer type", choices=choices)
    submit = SubmitField()

class DropDownForm(Form):
    choice=TextField("Dropdown Choice",  [Required("Enter an dropdown choice")])
    submit = SubmitField()

class SubSectionAutoComplete(Form):
    phrase = TextAreaField("Phrase(s)", [Required("Enter a phrase")])
    submit = SubmitField()

class QPulseDetailsForm(Form):
    username = TextField("Q-Pulse Username")
    password = PasswordField("Q-Pulse Password")
    password_reenter = PasswordField("Re-Enter Q-Pulse Password")
    submit = SubmitField("Update Details")

class ChangePassword(Form):
    old_password = PasswordField("Old Password")
    new_password = PasswordField("New Password")
    new_password_check = PasswordField("Re-Enter New Password")
    submit = SubmitField()
class ReserPassword(Form):
    email = TextField("Registered Email")
    new_password = PasswordField("New Password")
    new_password_check = PasswordField("Re-Enter New Password")
    submit = SubmitField()