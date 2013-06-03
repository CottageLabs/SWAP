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
        student = models.Student()
        student.save_from_form(request)
        
        return redirect(url_for('.complete'))


def dropdowns(model,key='name'):
    qry = {
        'query':{'match_all':{}},
        'size': 0,
        'facets':{}
    }
    qry['facets'][key] = {"terms":{"field":key+app.config['FACET_FIELD'],"order":'term', "size":100000}}
    klass = getattr(models, model[0].capitalize() + model[1:] )
    r = klass().query(q=qry)
    return [i.get('term','') for i in r.get('facets',{}).get(key,{}).get("terms",[])]


