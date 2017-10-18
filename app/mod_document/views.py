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
from sqlalchemy import and_, or_, case
from flask import render_template, request, url_for, redirect, Blueprint
from flask.ext.login import login_required, current_user
from app.views import admin_permission
from app.models import *
from app.competence import s
from forms import *

document = Blueprint('document', __name__, template_folder='templates')

# queries
def get_doc_info(c_id):
    """
    Method to get doc infor from database

    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    competence_list = s.query(Competence).\
        join(Users). \
        filter(Competence.id == c_id).\
        values(Competence.title, Competence.qpulsenum, Competence.scope,
               (Users.first_name + ' ' + Users.last_name).label('name'), Competence.current_version)
    for c in competence_list:
        return c

def get_subsections(c_id):
    """
    Method to get subsection info from database
    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    subsection_list = s.query(Subsection). \
        join(Section). \
        join(Competence). \
        join(Documents).\
        filter(Subsection.c_id == c_id). \
        values(Subsection.name, Subsection.comments, Documents.qpulse_no, Section.constant, Subsection.evidence)
    return subsection_list

#methods

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

def export_document(c_id):
    """
    Method to export a blank competence document to PDF
    :param c_id: ID of competence to be returned
    :type c_id: INT
    :return:
    """
    document = Document()

    # Get variables using queries
    print "Going to list stuff in comp_list"
    comp = get_doc_info(c_id)


    subsec_list = get_subsections(c_id)
    print "Going to list stuff in subsec_list"
    for sub in subsec_list:
        print(sub)

    # Header

    title = comp.title
    docid = comp.qpulsenum

    # Footer
    version_no = comp.current_version
    author = comp.name

    # Competence details
    scope = comp.scope


    # pagination


    # Make main document
    html_out = render_template('export_to_pdf.html', title=title, docid=docid, scope=scope)
    html = HTML(string=html_out)

    main_doc = html.render(stylesheets=[CSS('static/css/simple_report.css')])

    exists_links = False

    # Add headers and footers
    # header = html.render(stylesheets=[CSS(string='div {position: fixed; top: 1cm; left: 1cm;}')])
    header_out = render_template('header.html', title=title, docid=docid)
    header_html = HTML(string=header_out)
    header = header_html.render(stylesheets=[CSS('static/css/simple_report.css'), CSS(string='div {position: fixed; top: -2.7cm; left: 0cm;}')])

    header_page = header.pages[0]
    exists_links = exists_links or header_page.links
    header_body = get_page_body(header_page._page_box.all_children())
    header_body = header_body.copy_with_children(header_body.all_children())

    # Template of footer
    footer_out = render_template('footer.html', version_no=version_no, author=author)
    footer_html = HTML(string=footer_out)
    footer = footer_html.render(stylesheets=[CSS('static/css/simple_report.css'), CSS(string='div {position: fixed; bottom: -2.1cm; left: 0cm;}')])

    footer_page = footer.pages[0]
    exists_links = exists_links or footer_page.links
    footer_body = get_page_body(footer_page._page_box.all_children())
    footer_body = footer_body.copy_with_children(footer_body.all_children())

    # Insert header and footer in main doc
    for i, page in enumerate(main_doc.pages):
        # if not i:
        #     continue

        page_body = get_page_body(page._page_box.all_children())
        page_body.children += header_body.all_children()
        page_body.children += footer_body.all_children()

        if exists_links:
            page.links.extend(header_page.links)
            page.links.extend(footer_page.links)

    main_doc.write_pdf(target="/home/bioinfo/chicks/stardb_download/test.pdf")
    return html_out

#views
@document.route('/export', methods=['GET', 'POST'])
def export_document_view():
    """
    View to export competence to PDF
    :return:
    """
    print(request.method)
    if request.method == 'GET':
        c_id = request.args.get('c_id')
        print('cid')
        print(c_id)
        html = export_document(c_id)
        return html