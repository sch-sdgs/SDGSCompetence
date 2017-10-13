from app.views import db
import datetime


class UserRolesRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(), unique=True, nullable=False)

    def __init__(self, role):
        self.role = role

    def __repr__(self):
        return '<UserRolesRef %r>' % self.role


class ValidityRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    months = db.Column(db.Integer, unique=False, nullable=False)

    def __init__(self, months):
        self.months = months

    def __repr__(self):
        return '<ValidityRef %r>' % self.months


class QuestionsRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(), unique=False, nullable=False)
    active = db.Column(db.BOOLEAN, unique=False, default=True, nullable=False, )

    def __init__(self, question):
        self.question = question

    def __repr__(self):
        return '<QuestionsRef %r' % self.question


class EvidenceTypeRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(), unique=True, nullable=False)

    def __init__(self, type):
        self.type = type

    def __repr__(self):
        return '<EvidenceTypeRef %r>' % self.type


class CoshhRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coshhitem = db.Column(db.String(), unique=True, nullable=False)


    def __init__(self, coshhitem):
        self.coshhitem = coshhitem

    def __repr__(self):
        return '<CoshhRef %r>' % self.coshhitem


class HealthSafetyRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(), unique=False, nullable=False)

    def __init__(self, question):
        self.question = question

    def __repr__(self):
        return '<HealthSafetyRef %r>' % self.question

class AssessmentStatusRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(), unique=True, nullable=False)


    def __init__(self, status):
        self.status = status

    def __repr__(self):
        return '<AssessmentStatusRef %r>' % self.status

class Competence (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(), unique=False)
    scope =  db.Column(db.String(), unique=False)
    qpulsenum = db.Column(db.String(), unique=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique = False)
    validity_period = db.Column(db.Integer,db.ForeignKey("ValidityRef"), unique =False )
    current_version = db.Column(db.Integer, unique =False, default=0)


    creator_rel = db.relationship("Users", lazy = 'joined', foreign_keys=[creator_id])
    validity_rel = db.relationship("ValidityRef", lazy = 'joined', foreign_keys=[validity_period])

    def __init__(self, title, scope, creator_id, validity_period):
        self.title=title
        self.scope=scope
        self.creator_id=creator_id
        self.validity_period=validity_period

    def __repr__(self):
        return '<Competence %r>' % self.title

class Users (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(), unique = True, nullable=False)
    first_name = db.Column(db.String(), unique=False, nullable=False)
    last_name = db.Column(db.String(), unique = False, nullable=False)
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





class Subsection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    c_id = db.Column(db.Integer, db.ForeignKey("Competence.id"), unique=False, nullable=False)
    s_id = db.Column(db.Integer, db.ForeignKey("Section.id"), unique=False, nullable=False)
    name = db.Column(db.String(), unique= False, nullable=False)
    evidence = db.Column(db.String(), unique=False, nullable=False)
    comments =db.Column( db.String(), unique=False, nullable=False)
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
    name = db.Column(db.String(), unique=False, nullable=False)
    constant = db.Column(db.BOOLEAN,  unique=False, nullable=False, default=True)

    def __init__(self, name):
        self.name = name


    def __repr__(self):
        return '<Section %r>' % self.name


class Assessments (db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(), unique=False, nullable=False)
    ss_id = db.Column(db.Integer, db.ForeignKey("Subsection.id"), unique=False, nullable=False)
    signoff_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("Users.id"), unique=False, nullable=False)
    date_completed = db.Columns(db.DATE, unique=False, nullable=False)
    date_expiry = db.Columns(db.DATE, unique=False, nullable=False)
    comments = db.Columns(db.String(), unique=False, nullable=False)
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

########### CPH


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
    case = db.Column(db.String(), unique=False, nullable=False)
    result = db.Column(db.String(), unique=False, nullable=False)
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
    name = db.Column(db.String(), unique=False, nullable=False)
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
    assessment_id = db