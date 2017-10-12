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


class Coshh(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    coshhitem = db.Column(db.String(), unique=True, nullable=False)


class HealthSafetyRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(), unique=False, nullable=False)


class AssessmentStatusRef(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(), unique=True, nullable=False)


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
    role_id = db.Column(db.Integer, db.ForeignKey("UserRolesRef.id"), unique=False, nullable=False)

    linemanager_rel = db.relationship("Users", lazy='joined', foreign_keys=[line_managerid])
    roleid_rel = db.relationship("UserRolesRef", lazy='joined', foreign_keys=[role_id])

    def __init__(self, login, first_name, last_name, active, line_managerid, role_id):
        self.login=login
        self.first_name=first_name
        self.last_name=last_name
        self.active=active
        self.line_managerid=line_managerid
        self.role_id=role_id
        self.date_created = str(datetime.datetime.now().strftime("%Y%m%d"))

    def __repr__(self):
        return '<Users %r>' % self.login


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

    def __init__(self, name, evidence, comments):
        self.name=name
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

    def __init__(self, status, date_completed, date_expiry,comments ):
        self.status=status
        self.date_completed=date_completed
        self.date_expiry=date_expiry
        self.comments=comments


    def __repr__(self):
        return '<Assessment %r>' % self.status




class Reassessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)