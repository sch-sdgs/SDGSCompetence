from flask_wtf import FlaskForm
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.fields import SubmitField, BooleanField, SelectMultipleField, SelectField, TextAreaField,PasswordField, StringField
from wtforms.validators import DataRequired
from app.competence import s
from app.models import *


class UserRoleForm(FlaskForm):
    role = StringField("Role",  [DataRequired("Enter a Username")])
    submit = SubmitField("Add Role")

class UserForm(FlaskForm):
    username = StringField("User Name", [DataRequired("Enter a Username")])
    firstname = StringField("First Name", [DataRequired("Enter a Username")])
    surname = StringField("Surname", [DataRequired("Enter a Username")])
    email = StringField("Email", [DataRequired("Enter a Username")])
    staff_no = StringField("Staff Number", [DataRequired("Enter a Username")])
    linemanager = StringField("Line Manager")
    jobrole = QuerySelectMultipleField("Job Role", query_factory=lambda: s.query(JobRoles).all(), get_label="job")
    userrole = QuerySelectMultipleField("User Role", query_factory=lambda: s.query(UserRolesRef).all(), get_label="role")
    section = QuerySelectField("Section", query_factory=lambda: s.query(Service).all(),
                                        get_label="name")
    submit = SubmitField()


class UserEditForm(FlaskForm):
    username = StringField("User Name", [DataRequired("Enter a Username")])
    firstname = StringField("First Name", [DataRequired("Enter a Username")])
    surname = StringField("Surname", [DataRequired("Enter a Username")])
    email = StringField("Email", [DataRequired("Enter a Username")])
    staff_no = StringField("Staff Number", [DataRequired("Enter a Username")])
    linemanager = StringField("Line Manager")
    jobrole = SelectMultipleField("Job Role")
    userrole = SelectMultipleField("User Role")
    section = SelectField("Section")
    submit = SubmitField()

class EvidenceTypeForm(FlaskForm):
    type=StringField("Evidence Type",  [DataRequired("Enter an Evidence Type")])
    submit = SubmitField()


class CompetenceCategoryForm(FlaskForm):
    category=StringField("Competence Type",  [DataRequired("Enter an Evidence Type")])
    submit = SubmitField()


class SectionForm(FlaskForm):
    name=StringField("Section Name",  [DataRequired("Enter a Section Name")])
    constant=BooleanField("Applicable to all competencies?")
    submit = SubmitField()

class ConstantSubSectionForm(FlaskForm):
    name=StringField("SubSection Name",  [DataRequired("Enter a Subsection Name")])
    section=SelectField("Section")
    submit = SubmitField()


class ValidityPeriodForm(FlaskForm):
    months=StringField("Validity period (months)",  [DataRequired("Enter a Duration in months")])
    submit = SubmitField()

class AssessmentStatusForm(FlaskForm):
    status=StringField("Assessment Status",  [DataRequired("Enter an Assessment Status")])
    submit = SubmitField()

class ServiceForm(FlaskForm):
    name=StringField("Service",  [DataRequired("Enter a service")])
    head_of_service=StringField("Head of Service", [DataRequired("Enter the head of service")])
    submit = SubmitField()

class JobRoleForm(FlaskForm):
    job=StringField("Job Role",  [DataRequired("Enter a job role")])
    submit = SubmitField()

class QuestionsForm(FlaskForm):
    question = StringField("Reassessment Question", [DataRequired("Enter a reassessment question")])
    choices=[("Free text", "Free text"),("Date","Date"), ("Yes/no","Yes/no"), ("Dropdown","Dropdown")]
    type = SelectField("Answer type", choices=choices)
    submit = SubmitField()

class DropDownForm(FlaskForm):
    choice=StringField("Dropdown Choice",  [DataRequired("Enter an dropdown choice")])
    submit = SubmitField()

class SubSectionAutoComplete(FlaskForm):
    phrase = TextAreaField("Phrase(s)", [DataRequired("Enter a phrase")])
    submit = SubmitField()

class QPulseDetailsForm(FlaskForm):
    username = StringField("Q-Pulse Username")
    password = PasswordField("Q-Pulse Password")
    password_reenter = PasswordField("Re-Enter Q-Pulse Password")
    submit = SubmitField("Update Details")

class ChangePassword(FlaskForm):
    old_password = PasswordField("Old Password")
    new_password = PasswordField("New Password")
    new_password_check = PasswordField("Re-Enter New Password")
    submit = SubmitField()

class ResetPassword(FlaskForm):
    email = StringField("Registered Email")
    new_password = PasswordField("New Password")
    new_password_check = PasswordField("Re-Enter New Password")
    submit = SubmitField()