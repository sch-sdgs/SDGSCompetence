#!flask/bin/python
from app.competence import app

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=80)
