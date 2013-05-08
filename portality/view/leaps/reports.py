import json
from copy import deepcopy

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models


blueprint = Blueprint('reports', __name__)


# show the options for viewing / downloading generated reports, or perhaps offer building via facetview
@blueprint.route('/')
def index():
    return render_template('leaps/reports/index.html')



