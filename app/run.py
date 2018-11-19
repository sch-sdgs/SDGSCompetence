#!flask/bin/python
from app.competence import app
from app.competence import db

if __name__ == "__main__":
    db.create_all()
    db.session.commit()

    app.run(debug=True, host='0.0.0.0', port=5012, threaded=True)