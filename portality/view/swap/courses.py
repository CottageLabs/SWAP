import json

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models
import portality.util


blueprint = Blueprint('courses', __name__)


# restrict everything in courses to logged in users
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
    if not current_user.is_course_manager:
        abort(401)
    

# view students that intend to apply to the college of the logged-in person
@blueprint.route('/')
def index():
    course = current_user.is_course_manager
    qry = {'query':{'bool':{'must':[{'term':{'archive'+app.config['FACET_FIELD']:'current'}}]}},'size':10000}
    if not isinstance(course,bool):
        qry['query']['bool']['must'].append({'term':{'course'+app.config['FACET_FIELD']:course}})

    q = models.Student().query(q=qry)
    students = [i['_source'] for i in q.get('hits',{}).get('hits',[])]
    
    return render_template('swap/courses/index.html', students=students)


# view particular student
@blueprint.route('/student/<appid>', methods=['GET','POST'])
def pae(appid):
    crse = current_user.is_course_manager
    student = models.Student.pull(appid)

    if student is None:
        abort(404)

    course = models.Course.pull_by_ccc(student.data.get('college',False),student.data.get('campus',False),student.data.get('course',False))
    
    if course is None:
        abort(404)

    if not isinstance(crse,bool) and course.id != crse:
        abort(404)

    if request.method == 'GET':
        if isinstance(crse,bool):
            cs = crse
        else:
            course.data['course']
        return render_template('swap/courses/student.html', student=student, course=cs)

    elif request.method == ' POST':
        # save the uploaded progression information for the student
        student.save_from_form(request)

        # then email the swap admin admin

        flash('Thank you very much for submitting your response. It has been saved.')
        return redirect('.index')




