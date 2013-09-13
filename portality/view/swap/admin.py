import json, time
from datetime import datetime

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect, url_for, send_file
from flask.ext.login import current_user

from portality.core import app
from portality.view.swap.forms import dropdowns
import portality.models as models

import cStringIO as StringIO



blueprint = Blueprint('admin', __name__)


# restrict everything in admin to logged in users who can view admin, and only accept posts from users that can do admin
@blueprint.before_request
def restrict():
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    elif request.method == 'POST' and not current_user.do_admin:
        abort(401)
    elif not current_user.view_admin:
        abort(401)

# build an admin page where things can be done
@blueprint.route('/')
def index():
    return render_template('swap/admin/index.html')


# update admin settings
@blueprint.route('/settings', methods=['GET','POST'])
def settings():
    if request.method == 'POST':
        inputs = request.json
        acc = models.Account.pull(app.config['SUPER_USER'][0])
        if 'settings' not in acc.data: acc.data['settings'] = {}
        for key in inputs.keys():
            acc.data['settings'][key] = inputs[key]
        acc.save()
        return ""
    else:
        abort(404)


# show a particular student record for editing
@blueprint.route('/student')
@blueprint.route('/student/<uuid>', methods=['GET','POST','DELETE'])
def student(uuid=None):
    if uuid is None:
        return render_template('swap/admin/students.html')

    if uuid == "new":
        student = None
    else:
        student = models.Student.pull(uuid)
        if student is None: abort(404)

    nats = dropdowns('student','nationality')
    if 'Scottish' in nats: nats.remove('Scottish')
    if 'English' in nats: nats.remove('English')
    if 'Irish' in nats: nats.remove('Irish')
    if 'Welsh' in nats: nats.remove('Welsh')
    nats = ['Scottish','English','Irish','Welsh'] + nats
    selections={
        "colleges": dropdowns('course','college'),
        "campus": dropdowns('course','campus'),
        "courses": dropdowns('course','course'),
        "simd_deciles": dropdowns('simd','simd_decile'),
        "simd_quintiles": dropdowns('simd','simd_quintile'),
        "archives": dropdowns('archive','name'),
        "studyskills": dropdowns('student','studyskills') + ['SE Humanities', 'East Science', 'Tayside Humanities', 'Tayside Nursing'],
        "nationalities": nats
    }

    if request.method == 'GET':
        return render_template('swap/admin/student.html', record=student, selections=selections)
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
            return render_template('swap/admin/student.html', record=student, selections=selections)
    

# allow for export of all supporting data models
@blueprint.route('/data/<model>/export')
def exportdata(model):
    # get all the records of this type of model
    klass = getattr(models, model[0].capitalize() + model[1:] )
    records = [i['_source'] for i in klass.query(size=10000000).get('hits',{}).get('hits',[])]
    # make a csv string of the records
    csvdata = StringIO.StringIO()
    firstrecord = True
    if len(records) != 0:
        keys = sorted(records[0].keys())
        if 'id' in keys: keys.remove('id')
        if 'created_date' in keys: keys.remove('created_date')
        if 'last_updated' in keys: keys.remove('last_updated')
    else:
        keys = []
    for record in records:
        # for the first one, put the keys on the first line, otherwise just newline
        if firstrecord:
            fk = True
            for key in keys:
                if fk:
                    fk = False
                else:
                    csvdata.write(',')
                csvdata.write('"' + key + '"')
            csvdata.write('\n')
            firstrecord = False
        else:
            csvdata.write('\n')
        # and then add each record as a line with the keys as chosen by the user
        firstkey = True
        for key in keys:
            if firstkey:
                firstkey = False
            else:
                csvdata.write(',')
            if isinstance(record[key],bool):
                if record[key]:
                    csvdata.write('"true"')
                else:
                    csvdata.write('"false"')
            elif isinstance(record[key],list):
                csvdata.write('"' + ",".join(record[key]) + '"')
            else:
                csvdata.write('"' + record[key].replace('"',"'") + '"')
    # dump to the browser as a csv attachment
    csvdata.seek(0)
    return send_file(
        csvdata, 
        mimetype='text/csv',
         attachment_filename="swap_" + model + "_export_" + datetime.now().strftime("%d%m%Y%H%M") + ".csv",
        as_attachment=True
    )
    
# do updating of course / simd data
@blueprint.route('/data')
@blueprint.route('/data/<model>')
@blueprint.route('/data/<model>/<uuid>', methods=['GET','POST','DELETE'])
def data(model=None,uuid=None):
    selections={
        "course": dropdowns('course','course'),
        "college": dropdowns('course','college'),
        "campus": dropdowns('course','campus'),
        "region": dropdowns('course','region'),
        "classification": dropdowns('course','classification')
    }

    if request.method == 'GET':
        if model is None or model is not None and uuid is None:
            return render_template('swap/admin/data.html', selections=selections, model=model)
        else:
            if uuid == "new" or uuid is None:
                return render_template('swap/admin/datamodel.html', model=model, record=None, selections=selections)
            else:
                klass = getattr(models, model[0].capitalize() + model[1:] )
                rec = klass().pull(uuid)
                if rec is None:
                    abort(404)
                else:
                    return render_template('swap/admin/datamodel.html', model=model, record=rec, selections=selections)
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
            if uuid is not None and uuid != "new":
                rec = klass().pull(uuid)
                if rec is None:
                    abort(404)
                else:
                    rec.save_from_form(request)
                    flash("Your " + model + " has been updated", "success")
                    return render_template('swap/admin/datamodel.html', model=model, record=rec, selections=selections)
            else:
                rec = klass()
                rec.save_from_form(request)
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
        'swap/admin/archive.html', 
        currentcount=models.Student.query().get('hits',{}).get('total',0),
        archives=dropdowns('archive','name')
    )








