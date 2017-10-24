#!flask/bin/python
from app.competence import app

if __name__ == "__main__":
    app.run(debug=True, host='10.182.131.21', port=5017)
