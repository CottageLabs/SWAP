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
        return render_template('leaps/admin/import.html', model=model)
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
                    return render_template('leaps/admin/import.html')

            klass = getattr(models, model[0].capitalize() + model[1:] )

            if model.lower() in ['school']:
                for rec in records:
                    if 'contacts' not in rec:
                        rec['contacts'] = []
                        c = {}
                        if rec.get('contact_name',"") != "":
                            c["name"] = rec['contact_name']
                            del rec['contact_name']
                        if rec.get('contact_email',"") != "":
                            c["email"] = rec['contact_email']
                            del rec['contact_email']
                        if rec.get('contact_department',"") != "":
                            c["department"] = rec['contact_department']
                            del rec['contact_department']
                        if rec.get('contact_phone',"") != "":
                            c["phone"] = rec['contact_phone']
                            del rec['contact_phone']
                        if rec.get('password',"") != "":
                            c["password"] = rec['password']
                            del rec['password']
                        if len(c.keys()) > 0: rec['contacts'].append(c)
                    c = klass(**rec)
                    c.save()

            elif model.lower() in ['institution']:
                for rec in records:
                    if 'contacts' not in rec:
                        rec['contacts'] = []
                        c = {}
                        if rec.get('contact_name',"") != "":
                            c["name"] = rec['contact_name']
                            del rec['contact_name']
                        if rec.get('contact_email',"") != "":
                            c["email"] = rec['contact_email']
                            del rec['contact_email']
                        if rec.get('contact_department',"") != "":
                            c["department"] = rec['contact_department']
                            del rec['contact_department']
                        if rec.get('contact_phone',"") != "":
                            c["phone"] = rec['contact_phone']
                            del rec['contact_phone']
                        if len(c.keys()) > 0:
                            c['password'] = "m00shroom"
                            rec['contacts'].append(c)

                        c2 = {}
                        if rec.get('contact_name_2',"") != "":
                            c2["name"] = rec['contact_name_2']
                            del rec['contact_name_2']
                        if rec.get('contact_email_2',"") != "":
                            c2["email"] = rec['contact_email_2']
                            del rec['contact_email_2']
                        if rec.get('contact_department_2',"") != "":
                            c2["department"] = rec['contact_department_2']
                            del rec['contact_department_2']
                        if rec.get('contact_phone_2',"") != "" in rec:
                            c2["phone"] = rec['contact_phone_2']
                            del rec['contact_phone_2']
                        if len(c2.keys()) > 0:
                            c2['password'] = "m00shroom"
                            rec['contacts'].append(c2)

                    c = klass(**rec)
                    c.save()

            else:
                klass().bulk(records)
            
            time.sleep(1)
            checklen = klass.query(q="*")['hits']['total']
            
            flash(str(len(records)) + " records have been imported, there are now " + str(checklen) + " records.")
            return render_template('leaps/admin/import.html', model=model)

        except:
            flash("There was an error importing your records. Please try again.")
            return render_template('leaps/admin/import.html', model=model)



