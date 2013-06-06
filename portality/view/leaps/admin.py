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


# show a particular student record for editing
@blueprint.route('/student')
@blueprint.route('/student/<uuid>', methods=['GET','POST','DELETE'])
def student(uuid=None):
    if uuid is None:
        return render_template('leaps/admin/students.html')

    if uuid == "new":
        student = None
    else:
        student = models.Student.pull(uuid)
        if student is None: abort(404)

    selections={
        "schools": dropdowns('school'),
        "subjects": dropdowns('subject'),
        "levels": dropdowns('level'),
        "grades": dropdowns('grade'),
        "institutions": dropdowns('institution'),
        "advancedlevels": dropdowns('advancedlevel'),
        "local_authorities": dropdowns('school','local_authority'),
        "leaps_categories": dropdowns('school','leaps_category'),
        "simd_deciles": dropdowns('simd','simd_decile'),
        "simd_quintiles": dropdowns('simd','simd_quintile'),
        "archives": dropdowns('archive','name')
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
        new = False
        if student is None:
            new = True
            student = models.Student()
        
        student.save_from_form(request)

        if new:
            flash("New student record has been created", "success")
            return redirect(url_for('.student') + '/' + str(student.id))
        else:
            flash("Student record has been updated", "success")
            return render_template('leaps/admin/student.html', record=student, selections=selections)
    
    
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
@blueprint.route('/archive', methods=['GET','POST'])
def archives():
    if request.method == "POST":
        action = request.values['submit']
        if action == "Create":
            a = models.Archive( name=request.values['archive'] )
            a.save()
            flash('New archive named ' + a.data["name"] + ' created')
        elif action == "Move":
            a = models.Archive.pull_by_name(request.values['move_from'])
            b = models.Archive.pull_by_name(request.values['move_to'])
            if a is None or b is None:
                print b.id
                print a.id
                flash('Sorry. One of the archives you specified could not be identified...')
            else:
                lena = len(a)
                for i in a.children(justids=True):
                    ir = models.Student.pull(i)
                    ir.data["archive"] = b.data["name"]
                    ir.save()
                time.sleep(1)
                flash(str(lena) + ' records moved from archive ' + a.data["name"] + ' to archive ' + b.data["name"] + ', which now contains ' + str(len(b)) + ' records. Archive ' + a.data["name"] + ' still exists, but is now empty. Feel free to delete it if you wish, or use it to put more records in.')
        elif action == "Delete":
            a = models.Archive.pull_by_name(request.values['delete'])
            length = len(a)
            a.delete()
            flash('Archive ' + a.data["name"] + ' deleted, along with all ' + str(length) + ' records it contained.')

        time.sleep(1)

    return render_template(
        'leaps/admin/archive.html', 
        currentcount=models.Student.query().get('hits',{}).get('total',0),
        archives=dropdowns('archive','name')
    )


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






