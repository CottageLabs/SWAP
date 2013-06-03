import json
from copy import deepcopy

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models


blueprint = Blueprint('universities', __name__)


# restrict everything in admin to logged in users
@blueprint.before_request
def restrict():
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    if not current_user.is_institution:
        abort(401)
    

# build an admin page where things can be done
@blueprint.route('/')
def index():
    institution = current_user.institution

    q = models.Student().query(q={'query':{'bool':{'must':[{'term':{'applications.institution.exact':institution}},{'term':{'archive.exact':'current'}}]}},'size':10000})
    students = [i['_source'] for i in q.get('hits',{}).get('hits',[])]
    
    return render_template('leaps/universities/index.html', students=students, institution=institution)

# view students that intend to apply to the university of the logged-in person

# view PAE requests of relevant students

# submit an answer to a PAE request

# request to submit a change to an already submitted PAE

# printout a PAE request / PAE reply form

# export data about the relevant students and their PAE requests / supplied answers


