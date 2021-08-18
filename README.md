# SDGSCompetence

A user-friendly Flask-Python web application for recording and monitoring training in a department or team. The
entire app is Dockerised and therefore portable across different host servers. Currently, it runs a meinheld-gunicorn Docker image. 

### Requirements:
* Linux server (we have tested on Ubuntu) with Docker installed
* MySQL database
* A folder on host server to store uploaded documents

### Getting Started

1) Clone the code using `git clone https://github.com/sch-sdgs/SDGSCompetence.git`
2) Copy into app/config.py and fill out the following (or copy over an existing config.py):
    ```
    import os
    basedir = os.path.dirname(os.path.dirname(__file__))

    SQLALCHEMY_DATABASE_URI = <address_of_MySQL_db>

    SQLALCHEMY_TRACK_MODIFICATIONS = True
    WHOOSH_BASE = os.path.join(basedir + '/app/resources/')
    UPLOAD_FOLDER = os.path.join('/uploads')
    UPLOADED_FILES_DEST = os.path.join('/uploads')
    QPULSE_MODULE= { True / False } 

    ### for email notifications ###
    MAIL= { True / False }
    MAIL_SERVER = <mail_server>
    MAIL_PORT = <mail_port>
    MAIL_USERNAME = <mail_username> (can be None)
    MAIL_PASSWORD = <mail_password> (can be None)

    ORGANISATION = <organisation_name>
    ACTIVE_DIRECTORY = { True / False }

    TRAINER = "COMPETENT_STAFF,ADMIN"
    AUTHORISER = "COMPETENT_STAFF,ADMIN"
    ```
3) `cd` into SDGSCompetence directory
4) Build the Docker image: `docker build . -t competencedb:<version>`
5) Run the Docker: 
`docker run --name competencedb_<version> -v <uploads_folder>:/uploads 
-v /etc/ssl/certs/:/etc/ssl/certs/:ro 
-v /usr/local/share/ca-certificates/:/usr/local/share/ca-certificates/:ro 
-e CONFIG='/app/config.py' --link <mysql_docker> -p <host_port>:80 -dit competencedb:<version>`

6) On a browser (we recommend Chrome or Firefox, not IE), log onto: <IP_address>:<port_number>

