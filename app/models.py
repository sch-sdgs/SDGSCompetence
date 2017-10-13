from app.views import db
import datetime


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


class CoshhRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coshhitem = db.Column(db.String(1000), unique=True, nullable=False)


    def __init__(self, coshhitem):
        self.coshhitem = coshhitem

    def __repr__(self):
        return '<CoshhRef %r>' % self.coshhitem


class HealthSafetyRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, question):
        self.question = question

    def __repr__(self):
        return '<HealthSafetyRef %r>' % self.question

class ReagentRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reagent = db.Column(db.String(1000), unique=True, nullable=False)

    def __init__(self, reagent):
        self.reagent = reagent

    def __repr__(self):
        return '<HealthSafetyRef %r>' % self.reagent

class AssessmentStatusRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(1000), unique=True, nullable=False)


    def __init__(self, status):
        self.status = status

    def __repr__(self):
        return '<AssessmentStatusRef %r>' % self.status


class Competence (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(1000), unique=False,  nullable=False)
    scope =  db.Column(db.String(1000), unique=False, nullable=False)
    qpulsenum = db.Column(db.String(1000), unique=True, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique = False, nullable=False)
    validity_period = db.Column(db.Integer,db.ForeignKey("ValidityRef"), unique =False, nullable=False )
    current_version = db.Column(db.Integer, unique =False, default=0, nullable=False)


    creator_rel = db.relationship("Users", lazy = 'joined', foreign_keys=[creator_id])
    validity_rel = db.relationship("ValidityRef", lazy = 'joined', foreign_keys=[validity_period])

    def __init__(self, title, scope, creator_id, validity_period):
        self.title=title
        self.scope=scope
        self.creator_id=creator_id
        self.validity_period=validity_period

    def __repr__(self):
        return '<Competence %r>' % self.title

class CompetenceJobRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    competence_id = db.Column(db.Integer, db.ForeignKey("Competence.id"),  unique = False, nullable=False)
    jobrole_id = db.Column(db.Integer, db.ForeignKey("JobRoles.id"),  unique = False, nullable=False)

    jobroles_id_rel=db.relationship("JobRoles", lazy = 'joined', foreign_keys=[jobrole_id])
    competence_id_rel=db.relationship("Competence", lazy = 'joined', foreign_keys=[competence_id])

    def __init__(self, competence_id, jobrole_id):
        self.competence_id=competence_id
        self.jobrole_id=jobrole_id

    def __repr__(self):
        return '<CompetenceJobRelationship %r>' % self.id

class Users (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(1000), unique = True, nullable=False)
    first_name = db.Column(db.String(1000), unique=False, nullable=False)
    last_name = db.Column(db.String(1000), unique = False, nullable=False)
    date_created = db.Column(db.DATE, unique = False, nullable=False)
    last_login = db.Column(db.DATE, unique=False, nullable=True)
    active = db.Column(db.BOOLEAN, unique =False, default=True, nullable=False)
    line_managerid = db.Column(db.Integer, db.ForeignKey("Users.id"), unique = False, nullable=False)

    linemanager_rel = db.relationship("Users", lazy='joined', foreign_keys=[line_managerid])

    def __init__(self, login, first_name, last_name, active, line_managerid):
        self.login=login
        self.first_name=first_name
        self.last_name=last_name
        self.active=active
        self.line_managerid=line_managerid
        self.date_created = str(datetime.datetime.now().strftime("%Y%m%d"))

    def __repr__(self):
        return '<Users %r>' % self.login

class UserRoleRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)
    userrole_id=db.Column(db.Integer, db.ForeignKey("UserRolesRef.id"), unique=False, nullable=False)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_key=[user_id])
    userrole_id_rel = db.relationship("UserRolesRef", lazy='joined', foreign_key=[userrole_id])

    def __init__(self, user_id, userrole_id_rel):
        self.user_id=user_id
        self.userrole_id_rel=userrole_id_rel

    def __repr(self):
        return '<UserRolesRelationship % r>' % self.user_id

class UserJobRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)
    jobrole_id = db.Column(db.Integer, db.ForeignKey("JobRoles.id"), unique=False, nullable=False)

    user_id_rel = db.relationship("Users", lazy='joined', foreign_key=[user_id])
    jobroles_id_rel = db.relationship("JobRoles", lazy='joined', foreign_keys=[jobrole_id])

    def __init__(self, user_id, jobrole_id):
        self.user_id=user_id
        self.jobrole_id=jobrole_id

    def __repr__(self):
        return '<UserJobRelationship %r>' % self.id

class Subsection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("Competence.id"), unique=False, nullable=False)
    s_id = db.Column(db.Integer, db.ForeignKey("Section.id"), unique=False, nullable=False)
    name = db.Column(db.String(1000), unique= False, nullable=False)
    evidence = db.Column(db.String(1000), unique=False, nullable=False)
    comments =db.Column( db.String(1000), unique=False, nullable=False)
    intro = db.Column(db.Integer, unique=False, nullable = False, default=1)
    last = db.Column(db.Integer, unique=False, nullable = False, default=0)

    c_id_rel = db.relationship("Competence", lazy='joined', foreign_key=[id])
    s_id_rel = db.relationship("Section", lazy='joined', foreign_key=[id])

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

    def __init__(self, name):
        self.name = name


    def __repr__(self):
        return '<Section %r>' % self.name


class Assessments (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(1000), unique=False, nullable=False)
    ss_id = db.Column(db.Integer, db.ForeignKey("Subsection.id"), unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)
    date_completed = db.Columns(db.DATE, unique=False, nullable=False)
    date_expiry = db.Columns(db.DATE, unique=False, nullable=False)
    comments = db.Columns(db.String(1000), unique=False, nullable=False)
    reassessment_id = db.Columns(db.Integer, db.ForeignKey("Reassessment.id"), unique=False, nullable=False)

    ss_id_rel = db.relationship("Subsection", lazy='joined', foreign_key=[ss_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_key=[signoff_id])
    user_id_rel = db.relationship("Users", lazy='joined', foreign_key=[user_id])
    reassessment_id_rel = db.relationship("Reassessment", lazy='joined', foreign_key=[reassessment_id])

    def __init__(self, status, ss_id,user_id,  date_completed, date_expiry,comments,reassessment_id ):
        self.status=status
        self.ss_id=ss_id
        self.user_id=user_id
        self.date_completed=date_completed
        self.date_expiry=date_expiry
        self.comments=comments
        self.reassessment_id=reassessment_id


    def __repr__(self):
        return '<Assessment %r>' % self.status



class Reassessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assess_id = db.Column(db.Integer, db.ForeignKey("Assessments.id"), unique=False, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("QuestionsRef.id"), unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=True)
    date_completed = db.Columns(db.DATE, unique=False, nullable=True)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_key=[assess_id])
    question_id_rel = db.relationship("QuestionsRef", lazy='joined', foreign_key=[question_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_key=[signoff_id])

    def __init__(self, assess_id, question_id):

        self.assess_id=assess_id
        self.question_id=question_id

    def __repr__(self):
        return '<Reassessment %r>' % self.assess_id

class CaseBased(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column (db.Integer, db.ForeignKey("Assessments.id"), unique=False, nullable=False)
    case = db.Column(db.String(1000), unique=False, nullable=False)
    result = db.Column(db.String(1000), unique=False, nullable=False)
    is_correct = db.Column(db.BOOLEAN, unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_key=[assessment_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_key=[signoff_id])

    def __init__(self, case, result, is_correct):
        self.case=case
        self.result=result
        self.is_correct=is_correct

    def __repr__(self):
        return '<CaseBased> %r' % self.assessment_id

class Obx(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("Assessments.id"), unique=False, nullable=False)
    name = db.Column(db.String(1000), unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)
    is_correct = db.Column(db.BOOLEAN, unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_key=[assessment_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_key=[signoff_id])

    def __init__(self, name, is_correct):
        self.name=name
        self.is_correct =is_correct

    def __repr__(self):
        return '<CaseBased> %r' % self.assessment_id

class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("Assessments.id"), unique=False, nullable=False)
    file = db.Column(db.String(1000),unique=False, nullabl=False)
    is_correct = db.Column(db.BOOLEAN, unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_key=[assessment_id])
    signoff_id_rel = db.relationship("Users", lazy='joined', foreign_key=[signoff_id])

    def __init__(self, assessment_id, file, is_correct, signoff_id):
        self.assessment_id=assessment_id
        self.file=file
        self.is_correct=is_correct
        self.signoff_id=signoff_id

    def __repr__(self):
        return '<Upload %r>' % self.assessment_id

class AssessmentUploadRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id=db.Column(db.Integer, db.ForeignKey("Assessments.id"), unique=False, nullable=False)
    upload_id = db.Column(db.Integer, db.ForeignKey("Upload.id"), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_key=[assessment_id])
    upload_id_rel = db.relationship("Upload", lazy='joined', foreign_key=[upload_id])

    def __init__(self, assessment_id, upload_id):
        self.assessment_id=assessment_id
        self.upload_id=upload_id

    def __repr__(self):
        return '<AssessmentUploadRelationship %r>' % self.id

class AssessmentCaseBasedRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id=db.Column(db.Integer, db.ForeignKey("Assessments.id"), unique=False, nullable=False)
    casebased_id = db.Column(db.Integer, db.ForeignKey("CaseBased.id"), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_key=[assessment_id])
    casebased_id_rel = db.relationship("CaseBased", lazy='joined', foreign_key=[casebased_id])

    def __init__(self, assessment_id, casebased_id):
        self.assessment_id=assessment_id
        self.casebased_id=casebased_id

    def __repr__(self):
        return '<AssessmentCaseBasedRelationship %r>' % self.id

class AssessmentObxRelationship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id=db.Column(db.Integer, db.ForeignKey("Assessments.id"), unique=False, nullable=False)
    obx_id = db.Column(db.Integer, db.ForeignKey("Obx.id"), unique=False, nullable=False)

    assess_id_rel = db.relationship("Assessments", lazy='joined', foreign_key=[assessment_id])
    obx_id_rel = db.relationship("Obx", lazy='joined', foreign_key=[obx_id])

    def __init__(self, assessment_id, obx_id):
        self.assessment_id=assessment_id
        self.obx_id=obx_id

    def __repr__(self):
        return '<AssessmentObxRelationship %r>' % self.id

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
        return '<Service %r>' % self.job

class JobServiceRelationship(db.model):
    id = db.Column(db.Integer, primary_key=True)
    jobrole_id = db.Column(db.Integer, db.ForeignKey("JobRoles.id"), unique=False, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("Service.id"), unique=False, nullable=False)

    jobrole_id_rel = db.relationship("JobRoles", lazy='joined', foreign_key=[jobrole_id])
    service_id_rel = db.relationship("Service", lazy='joined', foreign_key=[service_id])

    def __init__(self, jobrole_id, service_id):
        self.jobrole_id=jobrole_id
        self.service_id=service_id

    def __repr__(self):
        return '<JobServiceRelationship % r>' % self.id

