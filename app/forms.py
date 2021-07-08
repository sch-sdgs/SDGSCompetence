
from flask_wtf import Form
from wtforms.fields import TextField, SubmitField, HiddenField, PasswordField, RadioField, BooleanField, SelectField, TextAreaField, DateField
from wtforms.ext.sqlalchemy.fields import QuerySelectField, QuerySelectMultipleField
from wtforms.validators import Required
from app.competence import *
from app.models import *


class Login(Form):
    username  = TextField("Username")
    password = PasswordField("Password")
    submit = SubmitField("Login")
    next = HiddenField("Next")

class RateEvidence(Form):
    comments = TextAreaField("Comments")
    assid = HiddenField("id")
    submit = SubmitField("Submit")
    expiry_date = DateField('Override Automated Expiry Date? (optional)', format='%Y-%m-%d')


from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from models import Users

# ...

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    first_name = StringField('First Name', validators=[DataRequired()])
    last_name = StringField('Last Name', validators=[DataRequired()])

    jobrole = QuerySelectMultipleField("Job Role", query_factory=lambda: s.query(JobRoles).all(), get_label="job")
    userrole = QuerySelectMultipleField("User Role", query_factory=lambda: s.query(UserRolesRef).all(),
                                        get_label="role")
    service_id = QuerySelectField("Department", query_factory=lambda: s.query(Service).all(),
                               get_label="name")
    organisation = StringField('Organisation', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    agree = BooleanField('I have read and understood the GDPR/Privacy statement')
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = Users.query.filter_by(login=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = Users.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')