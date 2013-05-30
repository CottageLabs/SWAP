'''
A forms system

Build a form template, build a handler for its submission, receive data from end users
'''

import json

from flask import Blueprint, request, abort, make_response, render_template, flash, redirect, url_for
from flask.ext.login import current_user

from portality.core import app

import portality.models as models


blueprint = Blueprint('forms', __name__)


# a forms overview page at the top level, can list forms or say whatever needs said about forms, or catch closed forms
@blueprint.route('/')
def intro():
    # make this an actual decision on whether or not survey is open or closed
    if True:
        return redirect(url_for('.student'))
    else:
        return render_template('leaps/survey/closed.html')
        

# a generic form completion confirmation page
@blueprint.route('/complete')
def complete():
    return render_template('leaps/survey/complete.html')


# form handling endpoint, by form name - define more for each form required
@blueprint.route('/student', methods=['GET','POST'])
def student():

    # for forms requiring auth, add an auth check here
    
    if request.method == 'GET':
        # TODO: if people are logged in it may be necessary to render a form with previously submitted data
        # selections should be named lists of available dropdown values
        # define which form to render
        response = make_response(
            render_template(
                'leaps/survey/survey.html', 
                selections={
                    "schools": dropdowns('school'),
                    "years": dropdowns('year'),
                    "subjects": dropdowns('subject'),
                    "levels": dropdowns('level'),
                    "grades": dropdowns('grade'),
                    "institutions": dropdowns('institution'),
                    "advancedlevels": dropdowns('advancedlevel')
                },
                data={}
            )
        )
        response.headers['Cache-Control'] = 'public, no-cache, no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response

    if request.method == 'POST':

        rec = {
            "qualifications": [],
            "interests": [],
            "applications": [],
            "experience": []
        }
        
        for k,v in enumerate(request.form.getlist('qualification_subject')):
            try:
                rec["qualifications"].append({
                    "subject": v,
                    "year": request.form.getlist('qualification_year')[k],
                    "level": request.form.getlist('qualification_level')[k],
                    "grade": request.form.getlist('qualification_grade')[k]
                })
            except:
                pass
        for k,v in enumerate(request.form.getlist('interest_title')):
            try:
                rec["interests"].append({
                    "title": v,
                    "brief_description": request.form.getlist('interest_brief_description')[k]
                })
            except:
                pass
        for k,v in enumerate(request.form.getlist('application_subject')):
            try:
                rec["applications"].append({
                    "subject": v,
                    "institute": request.form.getlist('application_institute')[k],
                    "level": request.form.getlist('application_level')[k]
                })
            except:
                pass
        for k,v in enumerate(request.form.getlist('experience_title')):
            try:
                rec["experience"].append({
                    "title": v,
                    "brief_description": request.form.getlist('experience_brief_description')[k],
                    "brief_description": request.form.getlist('experience_date_from')[k],
                    "brief_description": request.form.getlist('experience_date_to')[k]
                })
            except:
                pass

        for key in request.form.keys():
            if not key.startswith("qualification_") and not key.startswith("interest_") and not key.startswith("application_") and not key.startswith("experience_") :
                rec[key] = request.form[key]

        f = models.Student(**rec)
        f.save()
        
        return redirect(url_for('.complete'))


def dropdowns(model,key='name'):
    qry = {
        'query':{'match_all':{}},
        'size': 0,
        'facets':{}
    }
    qry['facets'][key] = {"terms":{"field":key+app.config['FACET_FIELD'],"order":'term', "size":10000}}
    klass = getattr(models, model[0].capitalize() + model[1:] )
    r = klass().query(q=qry)
    return [i.get('term','') for i in r.get('facets',{}).get(key,{}).get("terms",[])]


