import json
from copy import deepcopy

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models


from portality.view.leaps.imports import blueprint as imports
app.register_blueprint(imports, url_prefix='/import')


blueprint = Blueprint('admin', __name__)


# restrict everything in admin to logged in users
@blueprint.before_request
def restrict():
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    elif not current_user.view_only:
        abort(401)

# build an admin page where things can be done
@blueprint.route('/')
def index():
    return render_template('leaps/admin/index.html')


# search and view student records
# bulk change status of student records
@blueprint.route('/surveys')
def surveys():
    return render_template('leaps/admin/surveys.html')


# show a particular student record for editing
@blueprint.route('/student/<uuid>')
def student(uuid):
    if uuid == "new":
        student = models.Student()
    else:
        student = models.Student.pull(uuid)
        if student is None: abort(404)

    if request.method == 'GET':
        # TODO: this should obv render an editable template
        return render_template('leaps/admin/student.html')
    elif request.method == 'POST':
        # TODO: save the posted changes
        # do some validation / grabbing of other data if necessary
        pass
    
    
# do updating of schools / institutes / courses / pae answers / interview data
@blueprint.route('/data')
@blueprint.route('/data/<model>/<uuid>')
def data(model=None,uuid=None):
    if request.method == 'GET':
        if model is None:
            return render_template('leaps/admin/data.html')
        else:
            # which model to pull?
            if uuid == "new" or uuid is None:
                # TODO: render a new input form
                return render_template('leaps/admin/datamodel.html', model=model, record=None)
            else:
                klass = getattr(models, model[0].capitalize() + model[1:] )
                rec = klass().pull(uuid)
                if rec is None:
                    abort(404)
                else:
                    # TODO: this should render an editable copy of the datum
                    return render_template('leaps/admin/datamodel.html', model=model, record=rec)
    elif request.method == 'POST':
        if model is not None:
            klass = getattr(models, model[0].capitalize() + model[1:] )
            if uuid is not None:
                rec = klass().pull(uuid)
                rec.data = request.values
            else:
                rec = klass(**request.values)
            rec.save()
        else:
            abort(404)


# do archiving
@blueprint.route('/archives')
def archives():
    # get a list of all the archives in use and show them
    # allow for creating a new archive
    # allow for deleting an archive (and all its contents)
    # allow to move content of one archive to another (particularly "current archive" to others)
    return render_template('leaps/admin/archives.html')


# view / print pae forms
# view / print interview forms
@blueprint.route('/forms')
def forms():
    return render_template('leaps/admin/forms.html')


# do exporting
# explore / report
@blueprint.route('/export')
def export():
    return render_template('leaps/admin/export.html')


# add / remove users
@blueprint.route('/accounts')
def account():
    return render_template('leaps/admin/accounts.html')






