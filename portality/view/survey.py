'''
A survey system
'''

import json

from flask import Blueprint, request, abort, make_response, render_template, flash, redirect
from flask.ext.login import current_user

import portality.view.survey_forms as forms
import portality.models as models


blueprint = Blueprint('survey', __name__)


@blueprint.route('/')
def intro():
    # make this an actual decision on whether or not survey is open or closed
    if True:
        return render_template('leaps/survey/intro.html')
    else:
        return render_template('leaps/survey/closed.html')
        

@blueprint.route('/complete')
def complete():
    return render_template('leaps/survey/complete.html')


@blueprint.route('/<path:path>', methods=['GET','POST'])
def survey(path):
    klass = getattr(forms, path[0].capitalize() + path[1:] )
    form = klass(request.form, csrf_enabled=False)

    if request.method == 'GET':
        # TODO: populate the form with the data from the record pertaining to this student
        # if we appear to be traversing the survey
        # and if session ID matches, if limiting re-edit to same-session activities
        return render_template('leaps/survey/questionnaire.html', form=form)

    if request.method == 'POST':
        # need a check here for submission of a line in a mutli that is all blank, and ignore it
        # in which case, nothing new to save but allow previous / next
        if form.validate():
            # get the ID from the session
            _id = "1"
            # get any Survey data for this record
            temp = models.Survey.pull(_id)
            
            if form.next is None:
                # there is nowhere else to go, so save the real record and delete any incomplete stores
                if temp is None:
                    s = models.Student(id=_id)
                else:
                    s = models.Student(**temp.data)
                    temp.delete()
                # TODO: update student with form data
                s.save()
            else:
                if temp is None: temp = models.Survey(id=_id)
                # TODO: update the Survey record with form data
                temp.save()
            if request.form['submit'].lower() == "previous": 
                return redirect('/survey/' + form.previous)
            elif request.form['submit'].lower() == "submit": 
                return redirect('/survey/complete')
            else:
                return redirect('/survey/' + form.next)
        else:
            flash('Invalid form - please fix the errors below and try again.', 'error')
            return render_template('leaps/survey/questionnaire.html', form=form)



