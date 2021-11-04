import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
import inspect
import json
import os
import time
from docx import Document
from flask import Blueprint, jsonify
from flask_table import Table, Col
from sqlalchemy import and_, or_, case, func
from flask import render_template, request, url_for, redirect, Blueprint, send_from_directory
from flask_login import login_required, current_user
from app.views import admin_permission
from app.models import *
from app.competence import s
from app.qpulseweb import QPulseWeb
from forms import *
from sqlalchemy.orm import aliased
import uuid
from app.mod_competence import views as competence_views
from collections import OrderedDict
from app.competence import config

document = Blueprint('document', __name__, template_folder='templates')

# queries
def get_doc_info(c_id, version):
    """
    Method to get doc infor from database

    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """

    competence_list = s.query(CompetenceDetails).\
        filter(CompetenceDetails.c_id == c_id).filter(CompetenceDetails.intro == version).first()
    return competence_list

def get_subsections(c_id):
    """
    Method to get section and subsection info from database
    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    subsections = s.query(Subsection). \
        join(Section). \
        join(SectionSortOrder). \
        join(Competence).\
        filter(Subsection.c_id == c_id).\
        order_by(SectionSortOrder.sort_order.asc()).\
        order_by(Subsection.sort_order.asc()). \
        values(Subsection.name.label('subsec_name'),
               Subsection.comments,
               Section.name.label('sec_name'),
               Section.id,
               Section.constant,
               Subsection.evidence)
    subsection_list = []
    for i in subsections:
        subsection_list.append(i)
    return subsection_list

def get_qpulsenums(c_id, version):
    # qpulse_no_list = s.query(Documents).\
    #     filter(Documents.c_id == c_id).\
    #     values(Documents.qpulse_no)

    qpulse_no_list = s.query(Documents). \
        join(CompetenceDetails). \
        filter(CompetenceDetails.intro == version). \
        filter(CompetenceDetails.c_id == c_id)

    doc_list = []
    for i in qpulse_no_list:
        doc_list.append(i.qpulse_no)
    return doc_list

def get_latest_version(c_id):
    version = s.query(Competence).filter(Competence.id==c_id).\
        values(Competence.current_version)
    for v in version:
        return v

# evidence query - would this need to be filtered for each sub section - leave until Natalie has finished

# def get_evidence(c_id)
#     evidence = s.query(). \
#         join(Subsection). \
#         join(Assessments). \
#         join(Users)
#     filter(Subsection.c_id == c_id)
#     values(Evidence.name,
#            Evidence.s_id,
#
#            )
#    return

# methods

def get_page_body(boxes):
    """
    This method is used for creating the header and footer
    :param boxes:
    :return:
    """
    for box in boxes:
        if box.element_tag == 'body':
            return box

        return get_page_body(box.all_children())

def export_document(c_id, version):
    """
    Method to export a blank competence document to PDF
    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    document = Document()

    # Get variables using queries
    #comp = get_doc_info(c_id)
    #subsec = competence_views.get_subsections(c_id, v)
    #qpulse = get_qpulsenums(c_id)

    ## Get variables using competence_view query from mod_competence views
    # v = get_latest_version(c_id)[0]

    comp = get_doc_info(c_id, version)
    const = competence_views.get_constant_subsections(c_id, version)
    subsec = competence_views.get_subsections(c_id, version)
    if config.get("QPULSE_MODULE") == True:
        qpulse = get_qpulsenums(c_id, version)
        print(f"QPulse: {qpulse}")

    # Competence details
    title = comp.title
    # print "Qpulse number:"
    # print comp.qpulsenum
    # if config.get("QPULSE_MODULE") == True:
    #     docid = comp.qpulsenum
    # else:
    #     docid = None

    version_no = version

    author = comp.creator_rel.first_name + ' ' + comp.creator_rel.last_name
    authoriser = comp.approve_rel.first_name + ' ' + comp.approve_rel.last_name
    scope = comp.scope
    if comp.date_of_approval is not None:
        date_of_issue = comp.date_of_approval.strftime("%d-%m-%Y")
    else:
        date_of_issue = "Not Approved"

    # subsection details
    subsection = OrderedDict()

    for sub in subsec: ## This is each non-constant subsection
        sec_name = sub.sec_name
        subsection_name = sub.subsec_name
        comments = sub.comments
        evidence_type = sub.type
        value_list = [subsection_name, comments, evidence_type]#, sub_version,constant, sub_id]
        subsection.setdefault(sec_name,[]).append(value_list)

    #constant section details
    constant = OrderedDict()

    for c in const: # this is each constant subsection
        sec_type = c.sec_name #section name
        sec_name = c.subsec_name#name,
        sec_comments = c.comments
        evidence = c[3]
        value_list = [sec_name, sec_comments, evidence]
        constant.setdefault(sec_type,[]).append(value_list)

    #associated qpulse documents
    qpulse_list = {}
    if config.get("QPULSE_MODULE") == True:
        for qpulse_no in qpulse:
            #print(qpulse_no)
            d = s.query(QPulseDetails).first()
            qpulse_name = QPulseWeb().get_doc_by_id(d.username, d.password, qpulse_no)
            if qpulse_name == "False":
                qpulse_name = "There has been a problem locating this document in the Active register. " \
                           "Please contact the competence owner."
            #print(qpulse_name)
            qpulse_list[qpulse_no]=qpulse_name
    #print(qpulse_list)

    # evidence - this will be for downloading completed competences
    evidence_list = {}

    print('***Rendering main document***')
    # Make main document
    html_out = render_template('export_to_pdf.html', title=title, validity_period=comp.validity_rel.months, scope=scope, docid=c_id ,version_no=version_no, author=author, full_name=current_user.full_name, subsection=subsection, constant=constant, qpulse_list=qpulse_list)
    html = HTML(string=html_out)

    main_doc = html.render(stylesheets=[CSS('static/css/simple_report.css')])

    exists_links = False

    # Insert header and footer in main doc

    for page in main_doc.pages:
        header_out = render_template('header.html', title=title, docid=c_id)
        header_html = HTML(string=header_out)
        header = header_html.render(stylesheets=[CSS('static/css/simple_report.css'),
                                                 CSS(string='div {position: fixed; top: -2.7cm; left: 0cm;}')])

        header_page = header.pages[0]
        # exists_links = exists_links or header_page.links
        exists_header_links = header_page.links
        header_body = get_page_body(header_page._page_box.all_children())
        header_body = header_body.copy_with_children(header_body.all_children())

        # Template of footer
        footer_out = render_template('footer.html', version_no=version_no, author=author,
                                     full_name=current_user.full_name,
                                     authoriser=comp.approve_rel.first_name + " " + comp.approve_rel.last_name,
                                     date_of_issue=date_of_issue)
        footer_html = HTML(string=footer_out)
        footer = footer_html.render(stylesheets=[CSS('static/css/simple_report.css'),
                                                 CSS(string='div {position: fixed; bottom: -2.1cm; left: 0cm;}')])

        footer_page = footer.pages[0]
        exists_footer_links = footer_page.links
        footer_body = get_page_body(footer_page._page_box.all_children())
        footer_body = footer_body.copy_with_children(footer_body.all_children())

        page_body = get_page_body(page._page_box.all_children())
        page_body.children += header_body.all_children()
        page_body.children += footer_body.all_children()
        # if exists_links:
        #     page.links.extend(header_page.links)
        #     page.links.extend(footer_page.links)

        page.links.extend(header_page.links)
        page.links.extend(footer_page.links)


    outfile = str(uuid.uuid4())

    out_name = main_doc.write_pdf(target=app.config["UPLOAD_FOLDER"]+"/"+ outfile)
    return outfile
    #return html_out

#views
@document.route('/export', methods=['GET', 'POST'])
def export_document_view():
    """
    View to export competence to PDF
    :return:
    """
    if request.method == 'GET':
        c_id = request.args.get('c_id')
        version = request.args.get('version')
        outfile = export_document(c_id, version)
        uploads = app.config["UPLOAD_FOLDER"]
        filename = s.query(CompetenceDetails).filter(CompetenceDetails.c_id==c_id).first().title + ".pdf"
        return send_from_directory(directory=uploads, path=outfile, as_attachment=True, attachment_filename=filename)


@document.route('/export_trial', methods=['GET', 'POST'])
def export_trial_report():
    ids = [int(i) for i in request.args.get('ids').split(",")]
    uploads = app.config["UPLOAD_FOLDER"]


    current_data = s.query(CompetenceDetails).join(Competence).filter(CompetenceDetails.c_id.in_(ids)).filter(
        Competence.current_version == CompetenceDetails.intro).all()

    result = {}
    for i in current_data:
        print(i.title)
        #find out how many are trained and partially and in training
        #count how many subsections are in the competence
        number_of_subsections = s.query(Subsection).\
            join(Competence).\
            filter(and_(Subsection.intro <= Competence.current_version,or_(Subsection.last >= Competence.current_version,Subsection.last == None))).\
            filter(Subsection.c_id == i.c_id).count()
        #get all assessments by user?
        counts = s.query(func.count(Assessments.id).label("count"),
                         Assessments.user_id.label("user_id"),
                         Assessments.status.label("status_id"),
                         AssessmentStatusRef.status.label("status")).\
            join(AssessmentStatusRef).\
            join(Subsection).\
            join(Competence).\
            join(CompetenceDetails).\
            filter(and_(CompetenceDetails.intro <= Competence.current_version,
                        or_(CompetenceDetails.last >= Competence.current_version,
                            CompetenceDetails.last == None))).\
            filter(Subsection.c_id == i.c_id).\
            filter(Assessments.ss_id == Subsection.id).\
            group_by(Assessments.user_id).all()

        trained=0
        partial=0
        in_training=0
        expired=0
        for user_entry in counts: ### loop through users that are on this competence
            if (s.query(Users). \
                    filter(Users.id == user_entry.user_id). \
                    first()). \
                    active == 1: ### check if user is actually active
                print("User "+str(user_entry.user_id))
                statuses = []

                ### get all assessments for this user for this competence, put statuses in list
                users_assessments = s.query(Assessments). \
                    join(Subsection). \
                    filter(Assessments.user_id == user_entry.user_id). \
                    filter(Subsection.c_id == i.c_id). \
                    all()
                for entry in users_assessments:
                    if entry.status == 3: ### assessment is complete, check for expiry
                        if datetime.date.today() > entry.date_expiry:
                            statuses.append('Expired')
                        else:
                            statuses.append('Complete')
                    elif entry.status == 1 or entry.status == 7: ### assessment is active or waiting for sign-off
                        statuses.append('In training')

                ### from statuses list, decide on overall training status for this user for this competence, and add to counts
                if "In training" in statuses:
                    in_training += 1
                elif "Expired" in statuses:
                    expired+=1
                elif "Complete" in statuses:
                    if len(statuses) == int(number_of_subsections):
                        trained+=1
                    elif len(statuses) < int(number_of_subsections):
                        partial+=1

        #NEED TO TAKE INTO ACCOUNT EXPIRY
        #Counter(z)
        print(i.title)
        print(trained)
        print(expired)
        print(partial)
        print(in_training)
        result[i.c_id]={"title":i.title,
                        "trained":trained,
                        "expired":expired,
                        "partial":partial,
                        "training":in_training,
                        "category":i.category_rel.category}




    html_out = render_template('trial_view.html',result=result)
    html = HTML(string=html_out)

    main_doc = html.render(stylesheets=[CSS('static/css/simple_report_portrait.css')])

    exists_links = False

    # Add headers and footers
    # header = html.render(stylesheets=[CSS(string='div {position: fixed; top: 1cm; left: 1cm;}')])
    header_out = render_template('trial_view_header.html')
    header_html = HTML(string=header_out,base_url=request.url)
    header = header_html.render(
        stylesheets=[CSS('static/css/simple_report_portrait.css'), CSS(string='div {position: fixed; top: -2.7cm; left: 0cm;}')])

    header_page = header.pages[0]
    exists_links = exists_links or header_page.links
    header_body = get_page_body(header_page._page_box.all_children())
    header_body = header_body.copy_with_children(header_body.all_children())

    # Template of footer
    footer_out = render_template('trial_view_footer.html',user=current_user.full_name,date=str(datetime.datetime.now()))
    footer_html = HTML(string=footer_out)
    footer = footer_html.render(stylesheets=[CSS('static/css/simple_report_portrait.css'),
                                             CSS(string='div {position: fixed; bottom: -2.1cm; left: 0cm;}')])

    footer_page = footer.pages[0]
    exists_links = exists_links or footer_page.links
    footer_body = get_page_body(footer_page._page_box.all_children())
    footer_body = footer_body.copy_with_children(footer_body.all_children())

    # Insert header and footer in main doc

    for page in main_doc.pages:
        page_body = get_page_body(page._page_box.all_children())
        page_body.children += header_body.all_children()
        page_body.children += footer_body.all_children()
        if exists_links:
            page.links.extend(header_page.links)
            page.links.extend(footer_page.links)

    outfile = str(uuid.uuid4())

    out_name = main_doc.write_pdf(target=app.config["UPLOAD_FOLDER"] + "/" + outfile)

    return send_from_directory(directory=uploads, path=outfile, as_attachment=True, attachment_filename="training_report.pdf")