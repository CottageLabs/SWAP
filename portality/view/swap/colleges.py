import json

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models
import portality.util


blueprint = Blueprint('colleges', __name__)


# restrict everything in colleges to logged in users
# and only show when enabled
# and make college users sign the policy on first access
@blueprint.before_request
def restrict():
    adminsettings = models.Account.pull(app.config['SUPER_USER'][0]).data.get('settings',{})
    if not adminsettings.get('survey',False):
        return render_template('swap/admin/closed.html')
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    if not current_user.agreed_policy:
        return redirect('/account/policy?next=' + request.path)
    if not current_user.is_college:
        abort(401)
    

# view students that intend to apply to the college of the logged-in person
@blueprint.route('/')
def index():
    college = current_user.is_college
    qry = {'query':{'bool':{'must':[{'term':{'archive'+app.config['FACET_FIELD']:'current'}}]}},'size':10000}
    if not isinstance(college,bool):
        qry['query']['bool']['must'].append({'term':{'college'+app.config['FACET_FIELD']:college}})

    q = models.Student().query(q=qry)
    students = [i['_source'] for i in q.get('hits',{}).get('hits',[])]
    
    return render_template('swap/colleges/index.html', students=students, college=college)


# view particular student
@blueprint.route('/student/<appid>', methods=['GET','POST'])
def pae(appid):
    college = current_user.is_college

    student = models.Student.pull(appid)
    if student is None or not isinstance(college,bool) and student.data.get('college',"") != college:
        abort(404)

    if request.method == 'GET':
        return render_template('swap/colleges/student.html', student=student, college=college)

    elif request.method == ' POST':
        # save the uploaded progression information for the student
        student.save()

        # then email the swap admin admin

        flash('Thank you very much for submitting your response. It has been saved.')
        return redirect('.index')




