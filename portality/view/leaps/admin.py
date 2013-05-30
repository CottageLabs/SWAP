import json, time
from copy import deepcopy

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect, url_for
from flask.ext.login import current_user

from portality.core import app
from portality.view.leaps.forms import dropdowns
import portality.models as models



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
@blueprint.route('/student')
@blueprint.route('/student/<uuid>', methods=['GET','POST','DELETE'])
def student(uuid=None):
    if uuid is None:
        return redirect(url_for('.surveys'))
    if uuid == "new":
        student = None
    else:
        student = models.Student.pull(uuid)
        if student is None: abort(404)

    selections={
        "schools": dropdowns('school'),
        "years": dropdowns('year'),
        "subjects": dropdowns('subject'),
        "levels": dropdowns('level'),
        "grades": dropdowns('grade'),
        "institutions": dropdowns('institution'),
        "advancedlevels": dropdowns('advancedlevel'),
        "occupations": [],
        "languages": dropdowns('student','main_language_at_home')
    }

    if request.method == 'GET':
        return render_template('leaps/admin/student.html', record=student, selections=selections)
    elif ( request.method == 'POST' and request.values.get('submit','') == "Delete" ) or request.method == 'DELETE':
        if student is not None:
            student.delete()
            time.sleep(1)
            flash("Student " + str(student.id) + " deleted")
            return redirect(url_for('.student'))
        else:
            abort(404)
    elif request.method == 'POST':
        newrec = {}
        for val in request.values:
            if val not in ["submit"]:
                newrec[val] = request.values[val]
        if student is not None:
            newrec['id'] = student.id
            student.data = newrec
            student.save()
            flash("Student record has been updated", "success")
            return render_template('leaps/admin/student.html', record=student, selections=selections)
        else:
            student = models.Student(**newrec)
            student.save()
            flash("New student record has been created", "success")
            return redirect(url_for('.student') + '/' + str(student.id))
    
    
# do updating of schools / institutes / courses / pae answers / interview data
@blueprint.route('/data')
@blueprint.route('/data/<model>/<uuid>', methods=['GET','POST','DELETE'])
def data(model=None,uuid=None):
    if request.method == 'GET':
        if model is None:
            return render_template('leaps/admin/data.html')
        else:
            if uuid == "new" or uuid is None:
                return render_template('leaps/admin/datamodel.html', model=model, record=None)
            else:
                klass = getattr(models, model[0].capitalize() + model[1:] )
                rec = klass().pull(uuid)
                if rec is None:
                    abort(404)
                else:
                    # TODO: this should render an editable copy of the datum
                    return render_template('leaps/admin/datamodel.html', model=model, record=rec)
    elif ( request.method == 'POST' and request.values.get('submit','') == "Delete" ) or request.method == 'DELETE':
        if model is not None:
            klass = getattr(models, model[0].capitalize() + model[1:] )
            if uuid is not None:
                rec = klass().pull(uuid)
                if rec is not None:
                    rec.delete()
                    flash(model + " " + str(rec.id) + " deleted")
                    return redirect(url_for('.data'))
                else:
                    abort(404)
            else:
                abort(404)
        else:
            abort(404)    
    elif request.method == 'POST':
        if model is not None:
            klass = getattr(models, model[0].capitalize() + model[1:] )
            newrec = {}
            for val in request.values:
                if val not in ["submit"]:
                    newrec[val] = request.values[val]
            if uuid is not None and uuid != "new":
                rec = klass().pull(uuid)
                if rec is None:
                    abort(404)
                else:
                    newrec['id'] = rec.id
                    rec.data = newrec
                    rec.save()
                    flash("Your " + model + " has been updated", "success")
                    return render_template('leaps/admin/datamodel.html', model=model, record=rec)
            else:
                rec = klass(**newrec)
                rec.save()
                flash("Your new " + model + " has been created", "success")
                return redirect(url_for('.data') + '/' + model + '/' + str(rec.id))
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






