from sqlalchemy import create_engine
from app.competence import *

def create_connection(db_file):
    """
    Create a connection to the gel manager database
    :param db_file:
    :return:
    """

    engine = create_engine(db_file)
    conn = engine.connect()
    return conn

def get_assessments(conn):
    """ Gets all assessments information from active users from database"""
    sql = ''' SELECT users.serviceid, assessments.date_activated, assessments.date_completed, assessments.due_date, assessments.date_expiry, assessment_status_ref.status
    FROM assessments 
    INNER JOIN users ON assessments.user_id=users.id 
    INNER JOIN subsection ON assessments.ss_id=subsection.id 
    INNER JOIN competence ON subsection.c_id=competence.id
    INNER JOIN competence_details ON competence.id=competence_details.c_id
    INNER JOIN assessment_status_ref ON assessments.status=assessment_status_ref.id
    WHERE users.active="1" AND competence_details.intro=competence.current_version'''

    results = conn.execute(sql)

    assessments = results.fetchall()
    return assessments

def get_reassessments(conn):
    sql = ''' SELECT users.serviceid, reassessments.date_completed FROM assess_reassess_rel 
    INNER JOIN reassessments ON assess_reassess_rel.reassess_id=reassessments.id
    INNER JOIN assessments ON assess_reassess_rel.assess_id=assessments.id
    INNER JOIN users ON assessments.user_id=users.id 
    INNER JOIN subsection ON assessments.ss_id=subsection.id 
    INNER JOIN competence ON subsection.c_id=competence.id
    INNER JOIN competence_details ON competence.id=competence_details.c_id
    INNER JOIN assessment_status_ref ON assessments.status=assessment_status_ref.id
    WHERE users.active="1" AND competence_details.intro=competence.current_version AND 
    reassessments.is_correct="1" AND assessment_status_ref.status IN ("Complete", "Four Year Due")'''

    results = conn.execute(sql)

    reassessments = results.fetchall()
    return reassessments

def get_services(conn):
    sql = ''' SELECT id FROM service'''
    results = conn.execute(sql)
    services = results.fetchall()
    return services

def main():
    app.config.from_envvar('CONFIG', silent=False)
    config = app.config
    database = config.get('SQLALCHEMY_DATABASE_URI')

    c = create_connection(database)

    todays_date = datetime.date.today()

    counts = {
        'complete_assessments': {},
        'complete_reassessments': {},
        'expired_assessments': {},
        'expiring_assessments': {},
        'overdue_training': {},
        'activated_assessments': {},
        'activated_three_months_ago': {},
        'four_year_expiry_assessments': {}
    }

    services = get_services(c)
    for service in services:
        for service_id in service:
            print(service_id)
            for item in counts:
                counts[item][service_id] = 0

    assessments = get_assessments(c)

    for service_id, date_activated, date_completed, due_date, date_expiry, status in assessments:

        if status == "Complete" or status == "Four Year Due":
            if todays_date + relativedelta(months=-1) < date_completed: ### assessment has been completed in past month
                counts['complete_assessments'][service_id] +=1
            if todays_date > date_expiry:
                counts['expired_assessments'][service_id] +=1
            if todays_date + relativedelta(months=-49) < date_completed < todays_date + relativedelta(months=-48):
                counts['four_year_expiry_assessments'][service_id]+=1
            if todays_date < date_expiry < todays_date + relativedelta(months=+1):
                counts['expiring_assessments'][service_id] += 1

        elif status == "Active":
            if todays_date + relativedelta(months=-1) < date_activated: ### assessment has been activated in the past month
                counts['activated_assessments'][service_id] +=1
            if todays_date + relativedelta(months=-3) > date_activated: ###assessmented has been activated but not completed in 3 months
                counts['activated_three_months_ago'][service_id] +=1

        elif status in ["Active", "Assigned", "Failed", "Sign-Off"]:
            if todays_date > due_date:
                counts['overdue_training'][service_id] +=1

    reassessments = get_reassessments(c)

    for service_id, date_completed in reassessments:
        if todays_date + relativedelta(months=-1) < date_completed:
            counts['complete_reassessments'][service_id]+=1

    for service in services:
        for service_id in service:
            sql = '''INSERT INTO monthly_report_numbers (date, expired_assessments, service_id, completed_assessments, completed_reassessments,
            overdue_training, activated_assessments, activated_three_month_assessments, four_year_expiry_assessments, expiring_assessments) VALUES (%s, %s, %s, %s, %s,%s, %s, %s, %s, %s)'''

            c.execute(sql, [(todays_date, counts['expired_assessments'][service_id], service_id, counts['complete_assessments'][service_id],
                            counts['complete_reassessments'][service_id], counts['overdue_training'][service_id], counts['activated_assessments'][service_id],
                            counts['activated_three_months_ago'][service_id], counts['four_year_expiry_assessments'][service_id], counts['expiring_assessments'][service_id])])


    # for service in services:
    #     service_id = service.id
    #     entry = MonthlyReportNumbers(service_id=service_id,
    #                                  expired_assessments=counts['expired_assessments'][service_id],
    #                                  completed_assessments=counts['complete_assessments'][service_id],
    #                                  completed_reassessments=counts['complete_reassessments'][service_id],
    #                                  overdue_training=counts['overdue_training'][service_id],
    #                                  activated_assessments=counts['activated_assessments'][service_id],
    #                                  activated_three_month_assessments=counts['activated_three_months_ago'][service_id],
    #                                  four_year_expiry_assessments=counts['four_year_expiry_assessments'][service_id])
    #     s.add(entry)
    #     s.commit()


if __name__ == '__main__':
    main()