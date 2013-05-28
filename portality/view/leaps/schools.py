import json
from copy import deepcopy

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models


blueprint = Blueprint('schools', __name__)


# restrict everything in admin to logged in users
@blueprint.before_request
def restrict():
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    if not current_user.is_school:
        abort(401)
    

# build an admin page where things can be done
# view students of the school of the logged-in person that have submitted forms
@blueprint.route('/')
def index():
    school = "Fettes"#current_user.school
    q = models.Student().query(q={'query':{'bool':{'must':[{'term':{'school.exact':school}},{'term':{'archive.exact':'current'}}]}},'size':1000})
    students = [
        {"first_name":"mark","last_name":"macgillivray","date_of_birth":"10/07/1979","school_house":"farraline"},
        {"first_name":"misti","last_name":"jones","date_of_birth":"10/07/1986","school_house":"other"}
    ]
    
    return render_template('leaps/schools/index.html', students=students, school=school)

# offer an export of student data?

