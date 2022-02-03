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
    sql = ''' SELECT assessments.id, assessments.date_four_year_expiry, assessment_status_ref.status
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

def main():
    """
    Check all assessments for those that are due in 4 years, update the database
    """
    ### Set up the connection to the database
    app.config.from_envvar('CONFIG', silent=False)
    config = app.config
    database = config.get('SQLALCHEMY_DATABASE_URI')

    c = create_connection(database)

    ### Check for competencies which are <30 days from four year expiry
    todays_date = datetime.date.today()

    assessments = get_assessments(c)

    for id, date_four_year_expiry, status in assessments:
        if date_four_year_expiry < todays_date:
            sql = '''UPDATE assessments
            SET status = '8'
            WHERE id = %s'''

            c.execute(sql, id)

if __name__ == '__main__':
    main()
