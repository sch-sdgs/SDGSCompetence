from sqlalchemy import create_engine
from app.competence import *

def create_connection(db_file):
    """
    Create a connection to the database
    """
    engine = create_engine(db_file)
    conn = engine.connect()
    return conn

def get_assessments(conn):
    """ Gets all assessments information from active users from database"""
    sql = ''' SELECT assessments.id, assessments.date_four_year_expiry, assessments.date_expiry, 
    assessment_status_ref.status, assessments.user_id
    FROM assessments 
    INNER JOIN users ON assessments.user_id=users.id 
    INNER JOIN subsection ON assessments.ss_id=subsection.id 
    INNER JOIN competence ON subsection.c_id=competence.id
    INNER JOIN competence_details ON competence.id=competence_details.c_id
    INNER JOIN assessment_status_ref ON assessments.status=assessment_status_ref.id
    WHERE users.active="1" AND competence_details.intro=competence.current_version
    ORDER BY assessments.date_four_year_expiry DESC'''

    results = conn.execute(sql)

    assessments = results.fetchall()
    return assessments

def get_expiry_dates(conn):
    """Gets the closest expiry dates for each competency in the database"""
    sql = '''SELECT assessments.user_id,  
    MIN(assessments.date_expiry) AS 'min_date_expiry', 
    MIN(assessments.date_four_year_expiry) AS 'min_date_four_year_expiry',
    competence_details.title 
    FROM assessments 
    INNER JOIN users ON assessments.user_id = users.id 
    INNER JOIN subsection ON assessments.ss_id= subsection.id 
    INNER JOIN competence ON subsection.c_id = competence.id 
    INNER JOIN competence_details ON competence.id = competence_details.c_id 
    WHERE users.active = '1' AND competence_details.intro = competence.current_version 
    GROUP BY competence_details.id
    '''

    results = conn.execute(sql)

    expiry_dates = results.fetchall()
    return expiry_dates

def main():
    """
    Check all assessments for those that are due in 4 years, update the database
    """
    ### Set up the connection to the database
    app.config.from_envvar('CONFIG', silent=False)
    config = app.config
    database = config.get('SQLALCHEMY_DATABASE_URI')

    c = create_connection(database)

    ### Handle four year expiry dates - flag those which are expired
    todays_date = datetime.date.today()

    assessments = get_assessments(c)

    print("I am checking for four year expiries!")
    for id, date_four_year_expiry, status, user_id in assessments:
        if date_four_year_expiry is None:
            continue
        elif date_four_year_expiry <= todays_date:
            sql = '''UPDATE assessments
            SET status = '8'
            WHERE id = %s'''
            c.execute(sql, id)
            print("Found a four year expired competency! Flagging...")

    ### Check for expiring and expired competencies - send emails to users

    expiry_dates = get_expiry_dates(c)

    print("I am checking for expired and expiring competencies!")
    for user_id, min_date_expiry, min_date_four_year_expiry, title in expiry_dates:
        if min_date_four_year_expiry is None:
            continue
        elif min_date_four_year_expiry == todays_date:
            send_mail(user_id, f"You have an expired competency",
                      f"A competency: {title} has expired. This is a four year expiry - you will need to resubmit evidence as if "
                      f"you were completing this competency for the first time.")
        elif min_date_four_year_expiry == todays_date + relativedelta(days=7):
            send_mail(user_id, f"You have a competency expiring in 7 days",
                      f"A competency: {title} will expire in the next 7 days. This is a four year expiry - you will need to "
                      f"resubmit evidence as if you were completing this competency for the first time.")
        elif min_date_four_year_expiry == todays_date + relativedelta(days=30):
            send_mail(user_id, f"You have a competency expiring in 30 days",
                      f"A competency: {title} will expire in the next 30 days. This is a four year expiry - you will need to "
                      f"resubmit evidence as if you were completing this competency for the first time.")
        elif min_date_expiry is None:
            continue
        elif min_date_expiry == todays_date:
            send_mail(user_id, f"You have an expired competency",
                      f"A competency: {title} has expired - please complete a reassessment.")
        elif min_date_expiry == todays_date + relativedelta(days=7):
            send_mail(user_id, f"You have a competency expiring in 7 days",
                      f"A competency {title} will expire in the next 7 days - please complete a reassessment.")
        elif min_date_expiry == todays_date + relativedelta(days=30):
            send_mail(user_id, f"You have a competency expiring in 30 days",
                      f"A competency {title} will expire in the next 30 days - please complete a reassessment.")
        else:
            print(f"Something weird is happening with competencies for {user_id} - please check")


if __name__ == '__main__':
    main()
