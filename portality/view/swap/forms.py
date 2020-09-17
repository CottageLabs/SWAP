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
    adminsettings = models.Account.pull(app.config['SUPER_USER'][0]).data.get('settings',{})
    if adminsettings.get('survey',False):
        return redirect(url_for('.student'))
    else:
        return render_template('swap/survey/closed.html')
        

# a generic form completion confirmation page
@blueprint.route('/complete')
def complete():
    return render_template('swap/survey/complete.html')


# form handling endpoint, by form name - define more for each form required
@blueprint.route('/student', methods=['GET','POST'])
def student():

    # for forms requiring auth, add an auth check here
    
    if request.method == 'GET':
        # TODO: if people are logged in it may be necessary to render a form with previously submitted data
        nats = dropdowns('student','nationality')
        if 'Scottish' in nats: nats.remove('Scottish')
        if 'English' in nats: nats.remove('English')
        if 'Irish' in nats: nats.remove('Irish')
        if 'Welsh' in nats: nats.remove('Welsh')
        nats = ['Scottish','English','Irish','Welsh'] + nats
        schoollevels = dropdowns('schoollevel','name')
        if 'Intermediate 1' in schoollevels: schoollevels.remove('Intermediate 1')
        if 'Intermediate 2' in schoollevels: schoollevels.remove('Intermediate 2')
        if 'Standard Grade' in schoollevels: schoollevels.remove('Standard Grade')
        if 'Higher Grade' in schoollevels: schoollevels.remove('Higher Grade')
        schoollevels = ['Intermediate 1','Intermediate 2','Standard Grade','Higher Grade'] + schoollevels
        response = make_response(
            render_template(
                'swap/survey/survey.html', 
                selections={
                    "colleges": dropdowns('course','college'),
                    "campus": dropdowns('course','campus'),
                    "courses": dropdowns('course','course'),
                    "school_subjects": dropdowns('schoolsubject','name'),
                    "school_levels": schoollevels,
                    "post_school_levels": dropdowns('postschoollevel','name'),
                    "nationalities": nats
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
        'query':{
            'query_string':{
                'query': 'NOT disabled:*'
            }
        },
        'size': 0,
        'facets':{}
    }
    qry['facets'][key] = {"terms":{"field":key+app.config['FACET_FIELD'],"order":'term', "size":100000}}
    try:
        klass = getattr(models, model[0].capitalize() + model[1:] )
        r = klass().query(q=qry)
        return [i.get('term','') for i in r.get('facets',{}).get(key,{}).get("terms",[])]
    except:
        return []


