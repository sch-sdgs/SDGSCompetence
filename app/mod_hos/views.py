from app.competence import s, send_mail_unknown
from app.models import *
from flask import flash, render_template, request, url_for, redirect, Blueprint
from flask_login import login_required, current_user
from dateutil.relativedelta import relativedelta
from sqlalchemy.sql.expression import and_, or_
from app.mod_training.views import get_competence_summary_by_user
from app.views import hos_permission

from app.views import admin_permission
from app.activedirectory import UserAuthentication

hos = Blueprint('hos', __name__, template_folder='templates')

@hos.route('/service_overview')
@login_required
@hos_permission.require(http_exception=403)
def index():
    """
    populates the head of service page
    return: index template for head of service
    """
    """Get the service name"""
    service_name_query = s.query(Service) \
        .join(Users, Users.id == Service.head_of_service_id) \
        .filter(Service.head_of_service_id == int(current_user.database_id)) \
        .first()
    if service_name_query is None:
        service_name = "I HAVE HIT A DATABASE ERROR"
    else:
        service_name = service_name_query.name

    """Get data for service employees"""
    linereports = s.query(Users) \
        .join(Service, Service.id == Users.serviceid) \
        .filter(Service.name == service_name) \
        .filter(Users.active == 1) \
        .all()
    counts = {}
    active_count = 0
    assigned_count = 0
    complete_count = 0
    abandoned_count = 0
    signoff_count = 0
    failed_count = 0
    expiring_count = 0
    expired_count = 0

    for i in linereports:
        counts[i.id] = {}
        # Assigned competencies by staff member
        counts[i.id]["assigned"] = len(
            s.query(Assessments) \
            .join(AssessmentStatusRef) \
            .filter(Assessments.user_id == i.id) \
            .filter(AssessmentStatusRef.status == "Assigned") \
            .all()
        )
        assigned_count += counts[i.id]["assigned"]
        # Active competencies by staff member
        counts[i.id]["active"] = len(
            s.query(Assessments) \
                .join(AssessmentStatusRef) \
                .filter(Assessments.user_id == i.id) \
                .filter(AssessmentStatusRef.status == "Active") \
                .all()
        )
        active_count += counts[i.id]["active"]
        # Signed-off competencies by staff member
        counts[i.id]["sign-off"] = len(
            s.query(Assessments) \
                .join(AssessmentStatusRef) \
                .filter(Assessments.user_id == i.id) \
                .filter(AssessmentStatusRef.status == "Sign-Off") \
                .all()
        )
        signoff_count += counts[i.id]["sign-off"]
        # Complete competencies by staff member
        counts[i.id]["complete"] = len(
            s.query(Assessments) \
                .join(AssessmentStatusRef) \
                .filter(Assessments.user_id == i.id) \
                .filter(AssessmentStatusRef.status == "Complete") \
                .all()
        )
        complete_count += counts[i.id]["complete"]
        # Failed competencies by staff member
        counts[i.id]["failed"] = len(
            s.query(Assessments) \
                .join(AssessmentStatusRef) \
                .filter(Assessments.user_id == i.id) \
                .filter(AssessmentStatusRef.status == "Failed") \
                .all()
        )
        failed_count += counts[i.id]["failed"]
        # Obsolete competencies by staff member
        counts[i.id]["obsolete"] = len(
            s.query(Assessments) \
                .join(AssessmentStatusRef) \
                .filter(Assessments.user_id == i.id) \
                .filter(AssessmentStatusRef.status == "Obsolete") \
                .all()
        )
        # Abandoned competencies by staff member
        counts[i.id]["abandoned"] = len(
            s.query(Assessments) \
                .join(AssessmentStatusRef) \
                .filter(Assessments.user_id == i.id) \
                .filter(AssessmentStatusRef.status == "Abandoned") \
                .all()
        )
        abandoned_count += counts[i.id]["abandoned"]

    # Find expired and expiring competencies
    alerts = {}
    alerts["Assessments"] = {}
    for i in linereports:
        assessments = s.query(Assessments) \
            .filter(Assessments.user_id == i.id) \
            .all()
        for j in assessments:
            if j.date_expiry is not None:
                # Find expired assessments
                if datetime.date.today() > j.date_expiry:
                    if "expired" not in counts[i.id]:
                        counts[i.id]["expired"] = 0
                        counts[i.id]["expired"] += 1
                    else:
                        counts[i.id]["expired"] += 1
                    expired_count += 1
                # Find expiring assessments (within 1 month)
                elif datetime.date.today() + relativedelta(months=+1) > j.date_expiry:
                    if "expiring" not in counts[i.id]:
                        counts[i.id]["expiring"] = 0
                        counts[i.id]["expiring"] += 1
                    else:
                        counts[i.id]["expiring"] += 1
                    expiring_count += 1

    # Find complete and incomplete competencies
    competencies_incomplete = s.query(CompetenceDetails) \
        .join(Competence) \
        .filter(CompetenceDetails.creator_id == current_user.database_id) \
        .filter(Competence.current_version != CompetenceDetails.intro) \
        .filter(CompetenceDetails.date_of_approval == None) \
        .all()
    competencies_complete = s.query(CompetenceDetails) \
        .join(Competence) \
        .filter(CompetenceDetails.creator_id == current_user.database_id) \
        .filter(Competence.current_version == CompetenceDetails.intro) \
        .all()

    #Find assigned competencies
    assigned = s.query(Assessments) \
        .join(Subsection) \
        .join(Competence) \
        .join(CompetenceDetails) \
        .join(AssessmentStatusRef) \
        .filter(Assessments.user_id == current_user.database_id) \
        .group_by(Competence.id) \
        .filter(or_(AssessmentStatusRef.status == "Assigned",
                    AssessmentStatusRef.status == "Active",
                    AssessmentStatusRef.status == "Sign-Off")) \
        .all()

    all_assigned = []
    for k in assigned:
        all_assigned.append(get_competence_summary_by_user(
            c_id=k.ss_id_rel.c_id,
            u_id=current_user.database_id,
            version=k.version
        ))

    # Find active competencies
    active = s.query(Assessments) \
        .join(Subsection) \
        .join(Competence) \
        .join(CompetenceDetails) \
        .join(AssessmentStatusRef) \
        .group_by(CompetenceDetails.id) \
        .filter(Assessments.user_id == current_user.database_id) \
        .filter(CompetenceDetails.intro == Competence.current_version) \
        .filter(AssessmentStatusRef.status == "Active") \
        .all()

    # Find complete competencies
    complete = s.query(Assessments) \
        .join(Subsection) \
        .join(Competence) \
        .join(CompetenceDetails) \
        .join(AssessmentStatusRef) \
        .filter(Assessments.user_id == current_user.database_id) \
        .group_by(Subsection.c_id, Assessments.version) \
        .filter(AssessmentStatusRef.status.in_(["Complete", "Four Year Due"])) \
        .all()

    all_complete = []
    for l in complete:
        result = get_competence_summary_by_user(
            c_id=l.ss_id_rel.c_id,
            u_id=current_user.database_id,
            version=l.version
        )
        if result.completed != None:
            all_complete.append(result)

    # Find obsolete competencies
    obsolete = s.query(Assessments) \
        .join(Subsection) \
        .join(Competence) \
        .join(CompetenceDetails) \
        .join(AssessmentStatusRef) \
        .filter(Assessments.user_id == current_user.database_id) \
        .filter(and_(CompetenceDetails.intro <= Assessments.version,
                     or_(CompetenceDetails.last >= Assessments.version,
                         CompetenceDetails.last == None))) \
        .group_by(Competence.id) \
        .filter(AssessmentStatusRef.status.in_(["Obsolete"])) \
        .all()

    return render_template('service_overview.html', service_name=service_name, expired_count=expired_count, complete=all_complete, obsolete=obsolete, assigned_count=assigned_count,
                           active_count=active_count, signoff_count=signoff_count, failed_count=failed_count, complete_count=complete_count, linereports=linereports,
                           abandoned_count=abandoned_count, counts=counts, assigned=all_assigned, active=active, expiring_count=expiring_count)

def index():
    """
    shows the head of service homepage
    return: template service_overview.html
    """
    return render_template('service_overview.html')

