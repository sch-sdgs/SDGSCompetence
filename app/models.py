import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import backref
from app.competence import app
from passlib.hash import bcrypt
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy(app)

import sys

if sys.version_info >= (3, 0):
    enable_search = False
else:
    enable_search = True
    import flask_whooshalchemy as whooshalchemy


####################
###### Models ######
####################

class Assessments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer, db.ForeignKey("assessment_status_ref.id"), unique=False, nullable=False)
    ss_id = db.Column(db.Integer, db.ForeignKey("subsection.id"), unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    due_date = db.Column(db.DATE, unique=False, nullable=True)
    date_of_training = db.Column(db.DATE, unique=False, nullable=True)
    trainer_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    date_completed = db.Column(db.DATE, unique=False, nullable=True)
    date_expiry = db.Column(db.DATE, unique=False, nullable=True)
    date_assigned = db.Column(db.DATE, unique=False, nullable=False)
    assign_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    date_activated = db.Column(db.DATE, unique=False, nullable=True)
    comments = db.Column(db.String(1000), unique=False, nullable=True)
    version = db.Column(db.Integer, unique=False, nullable=True)
    date_four_year_expiry = db.Column(db.DATE, unique=False, nullable=True)

    ss_id_rel = db.relationship("Subsection", lazy='joined', foreign_keys=[ss_id])
    status_rel = db.relationship("AssessmentStatusRef", lazy='joined', foreign_keys=[status])
    trainer_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[trainer_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[signoff_id])
    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    assign_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[assign_id])

    evidence = db.relationship("AssessmentEvidenceRelationship", backref="assessments")

    def __init__(self, status, ss_id, user_id, assign_id, version, date_assigned, date_completed=None, date_expiry=None,
                 comments=None, due_date=None, date_of_training=None, trainer_id=None, date_activated=None,
                 signoff_id=None, date_four_year_expiry=None):
        self.status = status
        self.ss_id = ss_id
        self.user_id = user_id
        self.date_completed = date_completed
        self.date_expiry = date_expiry
        self.comments = comments
        self.due_date = due_date
        self.date_assigned = date_assigned
        self.assign_id = assign_id
        self.version=version
        self.date_of_training=date_of_training
        self.trainer_id = trainer_id
        self.date_activated=date_activated
        self.signoff_id = signoff_id
        self.date_four_year_expiry = date_four_year_expiry

    def __repr__(self):
        return '<Assessment %r>' % self.status


class AssessmentEvidenceRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), unique=False, nullable=False)
    evidence_id = db.Column(db.Integer, db.ForeignKey("evidence.id"), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_keys=[assessment_id])
    evidence_id_rel = db.relationship("Evidence", lazy='joined', foreign_keys=[evidence_id])

    def __init__(self, assessment_id, evidence_id):
        self.assessment_id = assessment_id
        self.evidence_id = evidence_id

    def __repr__(self):
        return '<AssessmentEvidenceRelationship %r>' % self.id


class AssessReassessRel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assess_id = db.Column(db.Integer, db.ForeignKey("assessments.id"), unique=False, nullable=False)
    reassess_id = db.Column(db.Integer, db.ForeignKey("reassessments.id"), unique=False, nullable=False)

    assess_rel = db.relationship("Assessments", lazy='joined', foreign_keys=[assess_id])
    reassess_rel = db.relationship("Reassessments", lazy='joined', foreign_keys=[reassess_id])

    def __init__(self, assess_id, reassess_id):
        self.assess_id = assess_id
        self.reassess_id = reassess_id

    def __repr__(self):
        return '<AssessReassessRel %r>' % self.id


class AssessmentStatusRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, status):
        self.status = status

    def __repr__(self):
        return '<AssessmentStatusRef %r>' % self.status


class Config(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(1000), unique=True, nullable=False)
    value = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return '<Config %r>' % self.organisation


class Competence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    current_version = db.Column(db.Integer, unique=False, default=0, nullable=False)
    obsolete = db.Column(db.BOOLEAN, unique=False, default=False, nullable=False)
    date_version = db.Column(db.DATE, unique=False, nullable=True)

    # competence_detail = db.relationship("CompetenceDetails", back_populates="competence")
    competence_detail = db.relationship("CompetenceDetails", lazy='joined', back_populates="competence")
    # competence_detail_current = db.relationship("CompetenceDetails",
    #                                     primaryjoin="and_(Competence.id== CompetenceDetails.c_id, Competence.current_version==CompetenceDetails.intro)",
    #                                     lazy='joined', back_populates="competence")

    def __init__(self, current_version=0, obsolete=False, date_version=None):
        self.current_version = current_version
        self.obsolete = obsolete
        self.date_version = date_version

    def __repr__(self):
        return '<Competence %r>' % self.id


class CompetenceCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(1000), unique=False, nullable=False)

    def __init__(self, category):
        self.category = category

    def __repr__(self):
        return '<CompetenceCategory %r>' % self.category


class CompetenceDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("competence.id"), unique=False, nullable=False)
    title = db.Column(db.String(1000), unique=False, nullable=False)
    scope = db.Column(db.String(1000), unique=False, nullable=False)
    qpulsenum = db.Column(db.String(1000), unique=True, nullable=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    date_created = db.Column(db.DATE, unique=False, nullable=False)
    approve_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    approved = db.Column(db.BOOLEAN, unique=False, default=None, nullable=True)
    date_of_approval = db.Column(db.DATE, unique=False, nullable=True)
    validity_period = db.Column(db.Integer, db.ForeignKey("validity_ref.id"), unique=False, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("competence_category.id"), unique=False, nullable=False)
    intro = db.Column(db.Integer, unique=False, nullable=False, default=1)
    last = db.Column(db.Integer, unique=False, nullable=True)
    date_expiry = db.Column(db.DATE, unique=False, nullable=True)
    expired = db.Column(db.BOOLEAN, unique=False, default=None, nullable=True)

    creator_rel = db.relationship("Users", lazy='joined', foreign_keys=[creator_id])
    approve_rel = db.relationship("Users", lazy='joined', foreign_keys=[approve_id])
    validity_rel = db.relationship("ValidityRef", lazy='joined', foreign_keys=[validity_period])
    category_rel = db.relationship("CompetenceCategory", lazy='joined', foreign_keys=[category_id])
    # c_id_rel = db.relationship("Competence", lazy='joined', foreign_keys=[c_id])
    competence = db.relationship("Competence",  back_populates="competence_detail", lazy='joined')
    rejection_rel = db.relationship("CompetenceRejectionReasons", lazy='joined')

    def __init__(self, c_id, title, scope, creator_id, validity_period, category_id, intro=1, approve_id=None,
                 approved=None):
        self.c_id = c_id
        self.title = title
        self.scope = scope
        self.creator_id = creator_id
        self.date_created = datetime.date.today()
        self.validity_period = validity_period
        self.category_id = category_id
        self.intro = intro
        self.approve_id = approve_id
        self.approved = approved

    def __repr__(self):
        return '<CompetenceDetails %r>' % self.title


class CompetenceJobRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    competence_id = db.Column(db.Integer, db.ForeignKey("competence.id"), unique=False, nullable=False)
    jobrole_id = db.Column(db.Integer, db.ForeignKey("job_roles.id"), unique=False, nullable=False)
    jobroles_id_rel = db.relationship("JobRoles", lazy='joined', foreign_keys=[jobrole_id])
    competence_id_rel = db.relationship("Competence", lazy='joined', foreign_keys=[competence_id])

    def __init__(self, competence_id, jobrole_id):
        self.competence_id = competence_id
        self.jobrole_id = jobrole_id

    def __repr__(self):
        return '<CompetenceJobRelationship %r>' % self.id


class CompetenceRejectionReasons(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DATETIME, unique=False, nullable=False)
    c_detail_id = db.Column(db.Integer, db.ForeignKey("competence_details.id"), unique=False, nullable=False)
    rejection_reason = db.Column(db.String(2000), unique=True, nullable=False)

    competence_details = db.relationship("CompetenceDetails", lazy='joined', foreign_keys=[c_detail_id])


class ConstantSubsections(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    s_id = db.Column(db.Integer, db.ForeignKey("section.id"), unique=False, nullable=False)
    item = db.Column(db.String(1000), unique=False, nullable=False)

    s_id_rel = db.relationship("Section", lazy='joined', foreign_keys=[s_id])

    def __init__(self, s_id, item):
        self.s_id = s_id
        self.item = item

    def __repr__(self):
        return '<ConstantSubsections %r>' % self.item


class CPDEvents(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    event_type = db.Column(db.Integer, db.ForeignKey("event_type_ref.id"), unique=False, nullable=False)
    date = db.Column(db.DATE, unique=False, nullable=False)
    event_role = db.Column(db.Integer, db.ForeignKey("event_role_ref.id"),unique=False, nullable=False)
    comments = db.Column(db.String(1000), nullable=True, unique=False)
    location = db.Column(db.String(50), nullable=False, unique=False)
    event_name = db.Column(db.String(200), nullable=False, unique=False)
    cpd_points = db.Column(db.String(20), unique=False, nullable=True)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    event_type_rel = db.relationship("EventTypeRef", lazy='joined', foreign_keys=[event_type])
    event_role_rel = db.relationship("EventRoleRef", lazy='joined', foreign_keys=[event_role])

    def __init__(self, user_id, event_type, date, event_role, location, event_name, comments=None, cpd_points=None):
        self.user_id = user_id
        self.event_type = event_type
        self.date = date
        self.event_role = event_role
        self.comments = comments
        self.location = location
        self.event_name = event_name
        self.cpd_points = cpd_points

    def __repr__(self):
        return '<CPDEvents %r>' % self.event_name


class Documents(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("competence_details.id"), unique=False, nullable=False)
    qpulse_no = db.Column(db.String(20), unique=False, nullable=False)

    c_id_rel = db.relationship("CompetenceDetails", lazy='joined', foreign_keys=[c_id])

    def __init__(self, c_id, qpulse_no):
        self.c_id = c_id
        self.qpulse_no = qpulse_no

    def __repr__(self):
        return '<Documents %r>' % self.qpulse_no


class DropDownChoices(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions_ref.id"), unique=False, nullable=False)
    choice = db.Column(db.String(1000), unique=False, nullable=False)

    question_id_rel = db.relationship("QuestionsRef", lazy='joined', foreign_keys=[question_id])

    def __init__(self, choice, question_id):
        self.question_id = question_id
        self.choice = choice

    def __repr__(self):
        return '<Dropdown Choices %r>' % self.id


class EventTypeRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False, unique=True)

    def __init__(self, type):
        self.type = type

    def __repr__(self):
        return '<EventTypeRef %r>' % self.type


class Evidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evidence = db.Column(db.String(1000), unique=False, nullable=True)
    evidence_type_id = db.Column(db.Integer, db.ForeignKey("evidence_type_ref.id"), unique=False, nullable=True)
    result = db.Column(db.String(1000), unique=False, nullable=True)
    is_correct = db.Column(db.BOOLEAN, unique=False, nullable=True)
    signoff_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    comments = db.Column(db.String(1000), unique=False, nullable=True)
    date_completed = db.Column(db.DATE, unique=False, nullable=True)
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[signoff_id])
    evidence_type_rel = db.relationship("EvidenceTypeRef", lazy='joined', foreign_keys=[evidence_type_id])

    assessments = db.relationship("AssessmentEvidenceRelationship", backref="evidence")
    reassess_rel = db.relationship("ReassessmentEvidenceRelationship", backref="reassess_rel")

    def __init__(self, is_correct, signoff_id, date, evidence_type_id, evidence=None, result=None, comments=None):
        self.is_correct = is_correct
        self.signoff_id = signoff_id
        self.date_completed = date
        self.evidence = evidence
        self.result = result
        self.comments = comments
        self.evidence_type_id = evidence_type_id

    def __repr__(self):
        return '<Evidence %r>' % self.id


class EventRoleRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False, unique=True)

    def __init__(self, role):
        self.role = role

    def __repr__(self):
        return '<EventRoleRef %r>' % self.role


class EvidenceTypeRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, type):
        self.type = type

    def __repr__(self):
        return '<EvidenceTypeRef %r>' % self.type


class Invites(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    invite_id = db.Column(db.String(1000),unique=True,nullable=False)
    first_name = db.Column(db.String(1000), unique=False, nullable=False)
    last_name = db.Column(db.String(1000), unique=False, nullable=False)
    email = db.Column(db.String(1000), unique=False, nullable=False)
    userid = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)

    user_rel = db.relationship("Users", lazy='joined', foreign_keys=[userid])

    def __init__(self,invite_id,first_name,last_name,email,userid):
        self.invite_id = invite_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.userid = userid


class JobRoles(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, job):
        self.job = job

    def __repr__(self):
        return '<JobRole %r>' % self.job


class MonthlyReportNumbers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DATE, unique=False, nullable=False)
    expired_assessments = db.Column(db.Integer, unique=False, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), unique=False, nullable=False)
    completed_assessments = db.Column(db.Integer, unique=False, nullable=False)
    completed_reassessments = db.Column(db.Integer, unique=False, nullable=False)
    overdue_training = db.Column(db.Integer, unique=False, nullable=False)
    activated_assessments = db.Column(db.Integer, unique=False, nullable=False)
    activated_three_month_assessments = db.Column(db.Integer, unique=False, nullable=False)
    four_year_expiry_assessments = db.Column(db.Integer, unique=False, nullable=False)
    expiring_assessments = db.Column(db.Integer, unique=False, nullable=True)

    service_id_rel = db.relationship("Service", lazy='joined', foreign_keys=[service_id])

    def __init__(self, service_id, expired_assessments, completed_assessments, completed_reassessments, overdue_training,
                 activated_assessments, activated_three_month_assessments, four_year_expiry_assessments, expiring_assessments):
        self.date = datetime.date.today()
        self.service_id = service_id
        self.expired_assessments = expired_assessments
        self.completed_assessments = completed_assessments
        self.completed_reassessments = completed_reassessments
        self.overdue_training = overdue_training
        self.activated_assessments = activated_assessments
        self.activated_three_month_assessments = activated_three_month_assessments
        self.four_year_expiry_assessments = four_year_expiry_assessments
        self.expiring_assessments = expiring_assessments

    def __repr__(self):
        return '<MonthlyReportNumbers %r>' % self.date


class PWReset(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    reset_key = db.Column(db.String(128), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    datetime = db.Column(db.DateTime(timezone=True), default=datetime.datetime.now)
    user = db.relationship("Users", lazy='joined')
    has_activated = db.Column(db.Boolean, default=False)


class QPulseDetails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=False, nullable=False)
    password = db.Column(db.String(100), unique=False, nullable=False)


class QuestionsRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(1000), unique=True, nullable=False)
    active = db.Column(db.BOOLEAN, unique=False, default=True, nullable=False)
    answer_type = db.Column(db.String(1000), unique=False, nullable=False)

    def __init__(self, question, answer_type):
        self.question = question
        self.answer_type = answer_type

    def __repr__(self):
        return '<QuestionsRef %r' % self.question


class Reassessments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    signoff_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    date_completed = db.Column(db.DATE, unique=False, nullable=True)
    is_correct = db.Column(db.BOOLEAN, unique=False, nullable=True)
    comments = db.Column(db.String(1000), unique=False, nullable=True)
    is_four_year = db.Column(db.Boolean, unique=False, nullable=True)

    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[signoff_id])
    assessments_rel = db.relationship("AssessReassessRel", lazy='joined')
    reassessment_questions = db.relationship("ReassessmentQuestions", back_populates="reassessment_id_rel")
    evidence_rel = db.relationship("ReassessmentEvidenceRelationship", backref="evidence_rel")

    def __init__(self, signoff_id, is_four_year=0):
        self.signoff_id = signoff_id
        self.is_four_year = is_four_year

    def __repr__(self):
        return '<Reassessments %r>' % self.id


class ReassessmentEvidenceRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reassessment_id = db.Column(db.Integer, db.ForeignKey("reassessments.id"), unique=False, nullable=False)
    evidence_id = db.Column(db.Integer, db.ForeignKey("evidence.id"), unique=False, nullable=False)

    def __init__(self, reassessment_id, evidence_id):
        self.reassessment_id = reassessment_id
        self.evidence_id = evidence_id

    def __repr__(self):
        return f"ReassessmentEvidenceRelationship id: {self.id}"


class ReassessmentQuestions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions_ref.id"), unique=False, nullable=False)
    answer = db.Column(db.String(1000), unique=False, nullable=False)
    reassessment_id = db.Column(db.Integer, db.ForeignKey("reassessments.id"), unique=False, nullable=False)

    question_id_rel = db.relationship("QuestionsRef", lazy='joined', foreign_keys=[question_id])
    reassessment_id_rel = db.relationship("Reassessments", lazy='joined', back_populates="reassessment_questions")


    def __init__(self, question_id, answer, reassessment_id):
        self.question_id = question_id
        self.answer = answer
        self.reassessment_id = reassessment_id

    def __repr__(self):
        return '<ReassessmentQuestions %r>' % self.id


class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=False, nullable=False)
    constant = db.Column(db.BOOLEAN, unique=False, nullable=False, default=True)

    # sort_order_rel = db.relationship("SectionSortOrder", back_populates="section_detail", lazy='joined')

    sort_order_rel = db.relationship("SectionSortOrder",backref="section_sort_order")

    def __init__(self, name, constant):
        self.name = name
        self.constant = constant

    def __repr__(self):
        return '<Section %r>' % self.name


class SectionSortOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("competence.id"), unique=False, nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey("section.id"), unique=False, nullable=False)
    sort_order = db.Column(db.Integer, unique=False, nullable=False)

    c_id_rel = db.relationship("Competence", lazy='joined', foreign_keys=[c_id])
    section_id_rel = db.relationship("Section", lazy='joined', foreign_keys=[section_id])
    # section_detail = db.relationship("Section", lazy='joined', back_populates="sort_order_rel")



    def __init__(self, c_id, section_id, sort_order):
        self.c_id = c_id
        self.section_id = section_id
        self.sort_order = sort_order

    def __repr__(self):
        return '<SectionSortOrder %r>' % self.section_id


class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), unique=True, nullable=True)
    head_of_service_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)

    head_of_service_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[head_of_service_id])

    def __init__(self, name, head_of_service_id):
        self.name = name
        self.head_of_service_id = head_of_service_id

    def __iter__(self):
        yield 'name', self.name
        yield 'head_of_service_id', self.head_of_service_id
        yield 'head_of_service_id_rel', self.head_of_service_id_rel

    def __repr__(self):
        return '<Service %r>' % self.name


class Subsection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("competence.id"), unique=False, nullable=False)
    s_id = db.Column(db.Integer, db.ForeignKey("section.id"), unique=False, nullable=False)
    name = db.Column(db.String(1000), unique=False, nullable=False)
    evidence = db.Column(db.Integer, db.ForeignKey("evidence_type_ref.id"), unique=False, nullable=False)
    comments = db.Column(db.String(1000), unique=False, nullable=True)
    intro = db.Column(db.Integer, unique=False, nullable=False, default=1)
    last = db.Column(db.Integer, unique=False, nullable=True)
    sort_order = db.Column(db.Integer, unique=False, nullable=True)

    c_id_rel = db.relationship("Competence", lazy='joined', foreign_keys=[c_id])
    s_id_rel = db.relationship("Section", lazy='joined', foreign_keys=[s_id])
    evidence_rel = db.relationship("EvidenceTypeRef", lazy='joined', foreign_keys=[evidence])

    def __init__(self, c_id, s_id, name, evidence, comments, sort_order, intro=1):
        self.name = name
        self.c_id = c_id
        self.s_id = s_id
        self.evidence = evidence
        self.comments = comments
        self.intro = intro
        self.sort_order = sort_order

    def __repr__(self):
        return '<Subsection %r>' % self.c_id


class SubsectionAutocomplete(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phrase = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, phrase):
        self.phrase = phrase

    def __repr__(self):
        return '<SubsectionAutocomplete %r>' % self.phrase


class Uploads(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(100), unique=False, nullable=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey("evidence.id"), unique=False, nullable=True)
    filename = db.Column(db.String(1000), unique=False, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    date_uploaded = db.Column(db.DATETIME, unique=False, nullable=False)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    evidence_rel = db.relationship("Evidence", lazy='joined', foreign_keys=[evidence_id])

    def __init__(self, uuid, filename, user_id, evidence_id):
        self.uuid = uuid
        self.filename = filename
        self.user_id = user_id
        self.evidence_id = evidence_id
        self.date_uploaded = datetime.datetime.today()

    def __repr__(self):
        return '<Uploads %r>' % self.uuid


class Users(db.Model):
    __searchable__ = ['first_name', 'last_name']

    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(1000), unique=True, nullable=False)
    first_name = db.Column(db.String(1000), unique=False, nullable=False)
    last_name = db.Column(db.String(1000), unique=False, nullable=False)
    email = db.Column(db.String(1000), unique=False, nullable=False)
    password = db.Column(db.String(1000), unique=False, nullable=True)
    staff_no = db.Column(db.String(1000), unique=False, nullable=True)
    band = db.Column(db.String(3), unique=False, nullable=True)
    date_created = db.Column(db.DATE, unique=False, nullable=False)
    last_login = db.Column(db.DATE, unique=False, nullable=True)
    active = db.Column(db.BOOLEAN, unique=False, default=True, nullable=False)
    line_managerid = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=True)
    serviceid = db.Column(db.Integer, db.ForeignKey("service.id"), unique=True, nullable=False)

    linemanager_rel = db.relationship("Users", remote_side=[id])

    service_rel = db.relationship("Service", lazy='joined', foreign_keys=[serviceid])


    def __init__(self, login, first_name, last_name, email, serviceid, active, password=None, line_managerid=None, staff_no=None):
        self.login = login
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.staff_no = staff_no
        self.active = active
        self.line_managerid = line_managerid
        self.serviceid = serviceid
        self.date_created = str(datetime.datetime.now().strftime("%Y%m%d"))
        if password != None:
            self.password = generate_password_hash(password)
        else:
            self.password = None

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


class UserJobRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    jobrole_id = db.Column(db.Integer, db.ForeignKey("job_roles.id"), unique=False, nullable=False)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    jobroles_id_rel = db.relationship("JobRoles", lazy='joined', foreign_keys=[jobrole_id])

    def __init__(self, user_id, jobrole_id):
        self.user_id = user_id
        self.jobrole_id = jobrole_id

    def __repr__(self):
        return '<UserJobRelationship %r>' % self.id


class UserRolesRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, role):
        self.role = role

    def __repr__(self):
        return '<UserRolesRef %r>' % self.role


class UserRoleRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=False, nullable=False)
    userrole_id = db.Column(db.Integer, db.ForeignKey("user_roles_ref.id"), unique=False, nullable=False)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_keys=[user_id])
    userrole_id_rel = db.relationship("UserRolesRef", lazy='joined', foreign_keys=[userrole_id])

    def __init__(self, user_id, userrole_id):
        self.user_id = user_id
        self.userrole_id = userrole_id

    def __repr(self):
        return '<UserRolesRelationship % r>' % self.user_id


class ValidityRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    months = db.Column(db.Integer, unique=True, nullable=False)

    def __init__(self, months):
        self.months = months

    def __repr__(self):
        return '<ValidityRef %r>' % self.months


class Videos(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DATETIME, unique=False, nullable=False)
    c_id = db.Column(db.Integer, db.ForeignKey("competence_details.id"), unique=False, nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    embed_code = db.Column(db.String(2000), unique=True, nullable=False)

    competence_details = db.relationship("CompetenceDetails", lazy='joined', foreign_keys=[c_id])

    def __init__(self,date,c_id,title,embed_code):
        self.date = datetime.datetime.today()
        self.c_id = c_id
        self.title = title
        self.embed_code = embed_code

    def __repr__(self):
        return '<Videos %r>' % self.title


########################
###### User Setup ######
########################


def __init__(self, username, password):
    self.username = username
    self.password = password


def __repr__(self):
    return "<User(username ='%s', password='%s')>" % (self.username, self.password)


if enable_search:
    whooshalchemy.whoosh_index(app, Users)
