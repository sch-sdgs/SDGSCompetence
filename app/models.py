import datetime
from flask_sqlalchemy import SQLAlchemy
from competence import app


db = SQLAlchemy(app)

import sys
if sys.version_info >= (3, 0):
    enable_search = False
else:
    enable_search = True
    import flask_whooshalchemy as whooshalchemy

class UserRolesRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, role):
        self.role = role

    def __repr__(self):
        return '<UserRolesRef %r>' % self.role


class ValidityRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    months = db.Column(db.Integer, unique=True, nullable=False)

    def __init__(self, months):
        self.months = months

    def __repr__(self):
        return '<ValidityRef %r>' % self.months


class QuestionsRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(1000), unique=True, nullable=False)
    active = db.Column(db.BOOLEAN, unique=False, default=True, nullable=False, )

    def __init__(self, question):
        self.question = question

    def __repr__(self):
        return '<QuestionsRef %r' % self.question


class EvidenceTypeRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, type):
        self.type = type

    def __repr__(self):
        return '<EvidenceTypeRef %r>' % self.type


class ConstantSubsections(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    s_id = db.Column(db.Integer, db.ForeignKey("section.id"), unique=False, nullable=False)
    item = db.Column(db.String(1000), unique=False, nullable=False)

    s_id_rel = db.relationship("Section", lazy='joined', foreign_keys=[s_id])

    def __init__(self, s_id, item):
        self.s_id=s_id
        self.item=item

    def __repr__(self):
        return '<ConstantSubsections %r>' % self.item


class AssessmentStatusRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(1000), unique=True, nullable=False)


    def __init__(self, status):
        self.status = status

    def __repr__(self):
        return '<AssessmentStatusRef %r>' % self.status

class CompetenceCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(1000), unique=False,  nullable=False)

    def __init__(self, category):
        self.category = category

    def __repr__(self):
        return '<CompetenceCategory %r>' % self.category

class Competence (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_version = db.Column(db.Integer, unique =False, default=0, nullable=False)
    obsolete = db.Column(db.BOOLEAN, unique=False, default=False, nullable=False)

    def __init__(self, current_version=0, obsolete=False):
        self.current_version = current_version
        self.obsolete = obsolete

    def __repr__(self):
        return '<Competence %r>' % self.title

class CompetenceDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("competence.id"), unique=False, nullable=False)
    title = db.Column(db.String(1000), unique=False, nullable=False)
    scope = db.Column(db.String(1000), unique=False, nullable=False)
    qpulsenum = db.Column(db.String(1000), unique=True, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    date_created = db.Column(db.DATE, unique = False, nullable=False)
    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    approved = db.Column(db.BOOLEAN, unique=False, default=False, nullable=True)
    date_of_approval = db.Column(db.DATE, unique = False, nullable=True)
    validity_period = db.Column(db.Integer, db.ForeignKey("validity_ref.id"), unique=False, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("competence_category.id"), unique=False, nullable=False)
    intro = db.Column(db.Integer, unique=False, nullable=False, default=1)
    last = db.Column(db.Integer, unique=False, nullable=True)

    creator_rel = db.relationship("Users", lazy='joined', foreign_keys=[creator_id])
    approve_rel = db.relationship("Users", lazy='joined', foreign_keys=[approve_id])
    validity_rel = db.relationship("ValidityRef", lazy='joined', foreign_keys=[validity_period])
    category_rel = db.relationship("CompetenceCategory", lazy='joined', foreign_keys=[category_id])
    c_id_rel = db.relationship("Competence", lazy='joined', foreign_keys=[c_id])

    def __init__(self, c_id, title, scope, creator_id, validity_period, category_id, intro, approve_id, approved=False):
        self.c_id = c_id
        self.title=title
        self.scope=scope
        self.creator_id=creator_id
        self.date_created = datetime.date.today()
        self.validity_period=validity_period
        self.category_id = category_id
        self.intro = intro
        self.approve_id = approve_id
        self.approved = approved

    def __repr__(self):
        return '<CompetenceDetails %r>' % self.title

class Documents(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("competence.id"),unique=False,  nullable=False)
    qpulse_no = db.Column(db.String(20),unique=False,  nullable=False)

    c_id_rel = db.relationship("Competence", lazy = 'joined', foreign_keys=[c_id])

    def __init__(self, c_id, qpulse_no):
        self.c_id=c_id
        self.qpulse_no=qpulse_no


    def __repr__(self):
        return '<Documents %r>' % self.qpulse_no

class CompetenceJobRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    competence_id = db.Column(db.Integer, db.ForeignKey("competence.id"),  unique = False, nullable=False)
    jobrole_id = db.Column(db.Integer, db.ForeignKey("job_roles.id"),  unique = False, nullable=False)

    jobroles_id_rel=db.relationship("JobRoles", lazy = 'joined', foreign_keys=[jobrole_id])
    competence_id_rel=db.relationship("Competence", lazy = 'joined', foreign_keys=[competence_id])

    def __init__(self, competence_id, jobrole_id):
        self.competence_id=competence_id
        self.jobrole_id=jobrole_id

    def __repr__(self):
        return '<CompetenceJobRelationship %r>' % self.id

class Users (db.Model):
    __searchable__ = ['first_name','last_name']

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(1000), unique = True, nullable=False)
    first_name = db.Column(db.String(1000), unique=False, nullable=False)
    last_name = db.Column(db.String(1000), unique = False, nullable=False)
    email = db.Column(db.String(1000), unique=False, nullable=False)
    staff_no = db.Column(db.String(1000), unique=False, nullable=False)
    band = db.Column(db.String(3), unique=False, nullable=False)
    date_created = db.Column(db.DATE, unique = False, nullable=False)
    last_login = db.Column(db.DATE, unique=False, nullable=True)
    active = db.Column(db.BOOLEAN, unique =False, default=True, nullable=False)
    line_managerid = db.Column(db.Integer, db.ForeignKey("users.id"), unique = False, nullable=True)
    serviceid = db.Column(db.Integer, db.ForeignKey("service.id"), unique=False, nullable=True)

    linemanager_rel = db.relationship("Users", lazy='joined', foreign_keys=[line_managerid])
    service_rel = db.relationship("Service", lazy='joined', foreign_keys=[serviceid])

    def __init__(self, login, first_name, last_name, email, serviceid, active, line_managerid=None, staff_no=None):
        self.login=login
        self.first_name=first_name
        self.last_name=last_name
        self.email =email
        self.staff_no=staff_no
        self.active=active
        self.line_managerid=line_managerid
        self.serviceid = serviceid
        self.date_created = str(datetime.datetime.now().strftime("%Y%m%d"))

    def __iter__(self):
        yield 'id', self.id
        yield 'login', self.login
        yield 'first_name', self.first_name
        yield 'last_name', self.last_name
        yield 'email', self.email
        yield 'date_created', self.date_created
        yield 'last_login', self.last_login
        yield 'active', self.active
        yield 'line_managerid', self.line_managerid
        yield 'line_managerrel', self.linemanager_rel

    def __repr__(self):
        return '<Users %r>' % self.login

class UserRoleRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    userrole_id=db.Column(db.Integer, db.ForeignKey("user_roles_ref.id"), unique=False, nullable=False)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    userrole_id_rel = db.relationship("UserRolesRef", lazy='joined', foreign_keys=[userrole_id])

    def __init__(self, user_id, userrole_id):
        self.user_id=user_id
        self.userrole_id=userrole_id

    def __repr(self):
        return '<UserRolesRelationship % r>' % self.user_id

class UserJobRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    jobrole_id = db.Column(db.Integer, db.ForeignKey("job_roles.id"), unique=False, nullable=False)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    jobroles_id_rel = db.relationship("JobRoles", lazy='joined', foreign_keys=[jobrole_id])

    def __init__(self, user_id, jobrole_id):
        self.user_id=user_id
        self.jobrole_id=jobrole_id

    def __repr__(self):
        return '<UserJobRelationship %r>' % self.id

class Subsection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("competence.id"), unique=False, nullable=False)
    s_id = db.Column(db.Integer, db.ForeignKey("section.id"), unique=False, nullable=False)
    name = db.Column(db.String(1000), unique= False, nullable=False)
    evidence = db.Column(db.Integer, db.ForeignKey("evidence_type_ref.id"), unique=False, nullable=False)
    comments =db.Column( db.String(1000), unique=False, nullable=False)
    intro = db.Column(db.Integer, unique=False, nullable = False, default=1)
    last = db.Column(db.Integer, unique=False, nullable = True)

    c_id_rel = db.relationship("Competence", lazy='joined', foreign_keys=[c_id])
    s_id_rel = db.relationship("Section", lazy='joined', foreign_keys=[s_id])
    evidence_rel =db.relationship("EvidenceTypeRef",  lazy='joined', foreign_keys =[evidence])

    def __init__(self,c_id, s_id, name, evidence,  comments):
        self.name=name
        self.c_id=c_id
        self.s_id=s_id
        self.evidence=evidence
        self.comments=comments


    def __repr__(self):
        return '<Subsection %r>' % self.c_id


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=False, nullable=False)
    constant = db.Column(db.BOOLEAN,  unique=False, nullable=False, default=True)

    def __init__(self, name, constant):
        self.name = name
        self.constant = constant


    def __repr__(self):
        return '<Section %r>' % self.name


class Assessments(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, db.ForeignKey("assessment_status_ref.id"), unique=False, nullable=False)
    ss_id = db.Column(db.Integer, db.ForeignKey("subsection.id"), unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    date_of_training=db.Column(db.DATE, unique=False, nullable=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    date_completed = db.Column(db.DATE, unique=False, nullable=True)
    date_expiry = db.Column(db.DATE, unique=False, nullable=True)
    date_assigned = db.Column(db.DATE, unique=False, nullable=False)
    assign_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    date_activated = db.Column(db.DATE, unique=False, nullable=True)
    comments = db.Column(db.String(1000), unique=False, nullable=True)
    is_reassessment = db.Column(db.BOOLEAN,  unique=False, default=False, nullable=False)

    ss_id_rel = db.relationship("Subsection", lazy='joined', foreign_keys=[ss_id])
    status_rel = db.relationship("AssessmentStatusRef", lazy='joined', foreign_keys=[status])
    trainer_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[trainer_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[signoff_id])
    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    assign_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[assign_id])

    def __init__(self, status, ss_id,user_id, assign_id, date_completed, date_expiry,comments,is_reassessment=0):
        self.status=status
        self.ss_id=ss_id
        self.user_id=user_id
        self.date_completed=date_completed
        self.date_expiry=date_expiry
        self.comments=comments
        self.is_reassessment=is_reassessment
        self.date_assigned = str(datetime.datetime.now().strftime("%Y%m%d"))
        self.assign_id = assign_id


    def __repr__(self):
        return '<Assessment %r>' % self.status



class Reassessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assess_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), unique=False, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions_ref.id"), unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    date_completed = db.Column(db.DATE, unique=False, nullable=True)
    answer = db.Column(db.String(1000), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_keys=[assess_id])
    question_id_rel = db.relationship("QuestionsRef", lazy='joined', foreign_keys=[question_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[signoff_id])

    def __init__(self, assess_id, question_id, answer):

        self.assess_id=assess_id
        self.question_id=question_id
        self.answer=answer

    def __repr__(self):
        return '<Reassessment %r>' % self.assess_id

class Evidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evidence = db.Column(db.String(1000), unique=False, nullable=True)
    result = db.Column(db.String(1000), unique=False, nullable=True)
    is_correct = db.Column(db.BOOLEAN, unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    comments = db.Column(db.String(1000), unique=False, nullable=True)
    date_completed = db.Column(db.DATE, unique=False, nullable=True)

    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[signoff_id])

    def __init__(self, is_correct, signoff_id, date, evidence=None, result=None, comments=None):
        self.is_correct = is_correct
        self.signoff_id = signoff_id
        self.date_completed = date
        self.evidence = evidence
        self.result = result
        self.comments = comments

    def __repr__(self):
        return '<Evidence %r>' % self.id


class AssessmentEvidenceRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id=db.Column(db.Integer, db.ForeignKey("assessments.id"), unique=False, nullable=False)
    evidence_id = db.Column(db.Integer, db.ForeignKey("evidence.id"), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_keys=[assessment_id])
    evidence_id_rel = db.relationship("Evidence", lazy='joined', foreign_keys=[evidence_id])

    def __init__(self, assessment_id, evidence_id):
        self.assessment_id=assessment_id
        self.evidence_id=evidence_id

    def __repr__(self):
        return '<AssessmentEvidenceRelationship %r>' % self.id

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, name):
        self.name=name

    def __repr__(self):
        return '<Service %r>' % self.name


class JobRoles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, job):
        self.job = job

    def __repr__(self):
        return '<JobRole %r>' % self.job

if enable_search:
    whooshalchemy.whoosh_index(app, Users)