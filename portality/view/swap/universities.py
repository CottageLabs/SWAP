import json

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models
import portality.util


blueprint = Blueprint('universities', __name__)


# restrict everything in universities to logged in users
# and only show when enabled
# and make university users sign the policy on first access
@blueprint.before_request
def restrict():
    adminsettings = models.Account.pull(app.config['SUPER_USER'][0]).data.get('settings',{})
    if not adminsettings.get('schools_unis',False):
        return render_template('leaps/admin/closed.html')
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    if not current_user.agreed_policy:
        return redirect('/account/policy?next=' + request.path)
    if not current_user.is_institution:
        abort(401)
    

# view students that intend to apply to the university of the logged-in person
@blueprint.route('/')
def index():
    institution = current_user.is_institution
    # TODO: add a filter so that only those records set as to be wanting PAE responses are shown
    qry = {'query':{'bool':{'must':[{'term':{'archive'+app.config['FACET_FIELD']:'current'}}]}},'size':10000}
    if not isinstance(institution,bool):
        qry['query']['bool']['must'].append({'term':{'applications.institution'+app.config['FACET_FIELD']:institution}})

    q = models.Student().query(q=qry)
    students = [i['_source'] for i in q.get('hits',{}).get('hits',[])]
    
    return render_template('leaps/universities/index.html', students=students, institution=institution)


# view particular PAE request
@blueprint.route('/pae/<appid>', methods=['GET','POST'])
def pae(appid):
    try:
        # return a student where one of their applications has the matching PAE ID
        # and where one of their applications is to the same institution as that of the current user
        # (may return some where the current user cannot respond, but is close enough - they have access to the student data anyway)
        institution = current_user.is_institution
        qry = {
            "query":{
                "bool":{
                    "must":[
                        {
                            "term":{
                                "applications.appid"+app.config['FACET_FIELD']:appid
                            }
                        }
                    ]
                }
            }
        }
        if not isinstance(institution,bool):
            qry['query']['bool']['must'].append({'term':{'applications.institution'+app.config['FACET_FIELD']:institution}})

        s = models.Student.query(q=qry)['hits']['hits'][0]['_source']['id']
        student = models.Student.pull(s)
        if student is None: abort(404)

    except:
        abort(404)

    application = {}
    for appn in student.data['applications']:
        if appn['appid'] == appid: application = appn
    
    if request.method == 'GET':
        if application.get('pae_reply_received',False):
            flash('This Pre-Application Enquiry was responded to on ' + application['pae_reply_received'] + ". It cannot be altered.")
        return render_template('leaps/universities/pae.html', student=student, institution=institution, application=application)

    elif request.method == ' POST':
        if application.get('pae_reply_received',False):
            abort(401)
        else:
            application['pae_reply_received'] = "" # TODO: this should be the current date
            application['consider'] = request.values['consider']
            application['conditions'] = request.values['conditions']
            application['summer_school'] = request.values['summer_school']

            # maybe change record status too, if first or last PAE answer
            if student.data['status'] == 'paes_requested':
                student.data['status'] = 'paes_in_progress'
            complete = True
            for appn in student.data['applications']:
                if appn.get('pae_reply_received',False):
                    complete = False
            if complete:
                student.data['status'] = 'paes_complete'

            student.save()

            # then email the lEAPS admin

            flash('Thank you very much for submitting your response. It has been saved.')
            return redirect('.index')




# printout a PAE request / PAE reply form
# use the pdf stuff in exports.py

# export data about the relevant students and their PAE requests / supplied answers
# use exporting stuff
# should be a rolling list of all student PAEs for this institution, and their provided answers or lack thereof
# in date submitted order
# so institutions can keep track of what they have and have not done yet



