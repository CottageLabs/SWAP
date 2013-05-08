'''
A forms system

Build a form template, build a handler for its submission, receive data from end users
'''

import json

from flask import Blueprint, request, abort, make_response, render_template, flash, redirect, url_for
from flask.ext.login import current_user

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
                    "schools": schools(),
                    "years": years(),
                    "subjects": subjects(),
                    "levels": levels(),
                    "grades": grades(),
                    "institutes": institutes(),
                    "advancedlevels": advancedlevels()
                },
                data={}
            )
        )
        response.headers['Cache-Control'] = 'public, no-cache, no-store, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        return response

    if request.method == 'POST':
        # assume client side validation
        # TODO: add any extra validation needed here

        form = request.form
        # TODO: do any transformations of form data to object model data
        f = models.Student(**form)
        # TODO: grab all the additional data based on user input, such as SIMD
        f.save()
        
        return redirect(url_for('.complete'))


# methods for getting data for selection dropdowns
def schools():
    return ['school1','school2']

def years():
    return ['year1','year2']

def subjects():
    return ['subject1','subject2']

def levels():
    return ['level1','level2']

def grades():
    return ['grade1','grade2']

def institutes():
    return ['int1','int2']

def advancedlevels():
    return ['agrade1','agrade2']





