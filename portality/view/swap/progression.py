'''
A forms system

Build a form template, build a handler for its submission, receive data from end users
'''

import json

from flask import Blueprint, request, render_template
from flask.ext.login import current_user

from portality.core import app
from portality.view.swap.forms import dropdowns

import portality.models as models


blueprint = Blueprint('progression', __name__)


# a forms overview page at the top level, can list forms or say whatever needs said about forms, or catch closed forms
@blueprint.route('/')
def progression():
    return render_template(
        'swap/progression.html',
        selections={
            "colleges": dropdowns('course','college'),
            "campus": dropdowns('course','campus'),
            "courses": dropdowns('course','course')
        }
    )
        




