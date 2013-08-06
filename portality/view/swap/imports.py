import json, csv, time

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models


blueprint = Blueprint('imports', __name__)


# restrict everything in admin to logged in users who can do admin
@blueprint.before_request
def restrict():
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    elif not current_user.do_admin:
        abort(401)


# build an import page
@blueprint.route('/')
@blueprint.route('/<model>', methods=['GET','POST'])
def index(model=None):
    if request.method == 'GET':
        return render_template('swap/admin/import.html', model=model)
    elif request.method == 'POST':
        try:
            records = []
            if "csv" in request.files.get('upfile').filename:
                upfile = request.files.get('upfile')
                #dialect = csv.Sniffer().sniff(upfile.read(1024))
                #upfile.seek(0)
                reader = csv.DictReader( upfile )#, dialect=dialect )
                records = [ row for row in reader ]
            elif "json" in request.files.get('upfile').filename:
                records = json.load(upfile)

            if model is None:
                model = request.form.get('model',None)
                if model is None:
                    flash("You must specify what sort of records you are trying to upload.")
                    return render_template('swap/admin/import.html')

            klass = getattr(models, model[0].capitalize() + model[1:] )

            klass().delete_all()

            if model.lower() in ['course']:
                for rec in records:
                    r = klass()
                    if rec.get('previous_name',"") != "":
                        rec['previous_name'] = rec['previous_name'].split(',')
                    else:
                        rec['previous_name'] = []
                    r.data = rec
                    r.save()

            else:
                klass().bulk(records)
            
            time.sleep(1)
            checklen = klass.query(q="*")['hits']['total']
            
            flash(str(len(records)) + " records have been imported, there are now " + str(checklen) + " records.")
            return render_template('swap/admin/import.html', model=model)

        except:
            flash("There was an error importing your records. Please try again.")
            return render_template('swap/admin/import.html', model=model)



