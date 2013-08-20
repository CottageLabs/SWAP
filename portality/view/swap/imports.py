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
                if model.lower() == 'ucas':
                    reader = csv.reader( upfile )
                else:
                    reader = csv.DictReader( upfile )
                records = [ row for row in reader ]
            elif "json" in request.files.get('upfile').filename:
                records = json.load(upfile)

            if model is None:
                model = request.form.get('model',None)
                if model is None:
                    flash("You must specify what sort of records you are trying to upload.")
                    return render_template('swap/admin/import.html')


            if model.lower() == 'ucas':
                # start with no student
                student = None
                
                # iterate each row in the csv, which has header rows of student 
                # data followed by multiple rows of student applications
                counter = 0
                failures = []
                updates = []
                for rec in records:
                    # iterate the row counter (in advance is fine because it 
                    # will be used as feedback in userland)
                    counter += 1
                    
                    # if the row starts with a number it is probably an appn
                    try:
                        float(rec[0])
                        probappn = True
                    except:
                        probappn = False
                    # if the row has data in col 0 and 2 it is probably a person
                    try:
                        if len(rec[0]) > 1 and len(rec[2]) > 1:
                            probperson = True
                        else:
                            probperson = False
                    except:
                        probperson = False
                    
                    if probperson:
                        # when hitting a person row, save the previous person
                        # if there was one, then reset back to none
                        if student is not None:
                            student.save()
                            updates.append('Updated student <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a>')
                            student = None
                        try:
                            # get the expected data from the row
                            last_name = rec[0]
                            first_name = rec[1]
                            date_of_birth = rec[2]
                            ucas_number = rec[3]
                            unknown = rec[4]
                            address_line_1 = rec[5]
                            address_line_2 = rec[6]
                            address_line_3 = rec[7]
                            address_line_4 = rec[8]
                            post_code = rec[9]
                            
                            # convert date of birth format if necessary
                            if '-' in date_of_birth:
                                parts = date_of_birth.split('-')
                                mon = "01"
                                if parts[1].lower() == 'jan':
                                    mon = "01"
                                elif parts[1].lower() == 'feb':
                                    mon = "02"
                                elif parts[1].lower() == 'mar':
                                    mon = "03"
                                elif parts[1].lower() == 'apr':
                                    mon = "04"
                                elif parts[1].lower() == 'may':
                                    mon = "05"
                                elif parts[1].lower() == 'jun':
                                    mon = "06"
                                elif parts[1].lower() == 'jul':
                                    mon = "07"
                                elif parts[1].lower() == 'aug':
                                    mon = "08"
                                elif parts[1].lower() == 'sep':
                                    mon = "09"
                                elif parts[1].lower() == 'oct':
                                    mon = "10"
                                elif parts[1].lower() == 'nov':
                                    mon = "11"
                                elif parts[1].lower() == 'dec':
                                    mon = "12"
                                
                                if len(str(parts[2])) == 2:
                                    if parts[2] > 50:
                                        year = str("19" + str(parts[2]))
                                    else:
                                        year = str("20" + str(parts[2]))
                                else:
                                    year = str(parts[2])

                                date_of_birth = str(parts[0]) + '/' + mon + '/' + year

                            # query the student index for a matching student
                            qry = {
                                'query':{
                                    'bool':{
                                        'must':[
                                            {'term':
                                                {'archive'+app.config['FACET_FIELD']:'current'}
                                            }
                                        ]
                                    }
                                }
                            }
                            # update query with ucas number search if available
                            # or else whatever else we can get
                            if len(ucas_number) > 1:
                                qry['query']['bool']['must'].append({'term':{'ucas_number'+app.config['FACET_FIELD']:ucas_number}})
                            else:
                                if len(last_name) > 1:
                                    qry['query']['bool']['must'].append({'match':{'last_name':{'query':last_name, 'fuzziness':0.8}}})
                                if len(date_of_birth) > 1:
                                    qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:date_of_birth}})
                                if len(post_code) > 1:
                                    qry['query']['bool']['should'] = [
                                        {'match':{'post_code':{'query':post_code, 'operator': 'and', 'fuzziness':0.9}}},
                                        {'term':{'post_code'+app.config['FACET_FIELD']:post_code.replace(' ','')}},
                                        {'term':{'post_code'+app.config['FACET_FIELD']:post_code.replace(' ','').lower()}}
                                    ]
                                    qry['query']['bool']['minimum_should_match'] = 1

                            try:
                                # try the query first time
                                q = models.Student().query(q=qry)
                                sid = q['hits']['hits'][0]['_source']['id']
                                student = models.Student.pull(sid)
                            except:
                                # try again ignoring ucas number
                                try:
                                    qry['query']['bool']['must'] = []
                                    if len(last_name) > 1:
                                        qry['query']['bool']['must'].append({'match':{'last_name':{'query':last_name, 'fuzziness':0.8}}})
                                    if len(date_of_birth) > 1:
                                        qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:date_of_birth}})
                                    if len(post_code) > 1:
                                        qry['query']['bool']['should'] = [
                                            {'match':{'post_code':{'query':post_code, 'operator': 'and', 'fuzziness':0.9}}},
                                            {'term':{'post_code'+app.config['FACET_FIELD']:post_code.replace(' ','')}},
                                            {'term':{'post_code'+app.config['FACET_FIELD']:post_code.replace(' ','').lower()}}
                                        ]
                                        qry['query']['bool']['minimum_should_match'] = 1
                                    q = models.Student().query(q=qry)
                                    sid = q['hits']['hits'][0]['_source']['id']
                                    student = models.Student.pull(sid)
                                except:
                                    # look for a unique match without using post code
                                    try:
                                        qry['query']['bool']['must'] = []
                                        if len(last_name) > 1:
                                            qry['query']['bool']['must'].append({'match':{'last_name':{'query':last_name, 'fuzziness':0.8}}})
                                        if len(date_of_birth) > 1:
                                            qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:date_of_birth}})
                                        q = models.Student().query(q=qry)
                                        if q['hits']['total'] == 1:
                                            sid = q['hits']['hits'][0]['_source']['id']
                                            student = models.Student.pull(sid)
                                        else:
                                            failures.append(str(q['hits']['total']) + ' possible matches for ' + first_name + ' ' + last_name + ' born on ' + date_of_birth + ' on row ' + str(counter) + ' as post codes did not match.')
                                    except:
                                        failures.append('Could not find a record in the system for ' + first_name + ' ' + last_name + ' in row ' + str(counter))

                            # if a student is found, and a ucas number is available, update the student record with it
                            if student is not None and len(ucas_number) > 1:
                                if not len(student.data.get('ucas_number',"")) > 1:
                                    student.data['ucas_number'] = ucas_number
                                    student.save()
                                    updates.append('Updated student <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a> with UCAS number ' + ucas_number)
                                
                        except:
                            # failed to read the person row
                            failures.append('Failed to read what appeared to be person details out of row ' + str(counter))

                    elif probappn:
                        # there should be a student already in this case
                        if student is not None:
                            if 'applications' not in student.data:
                                student.data['applications'] = []
                            try:
                                # get the appn data from the row
                                institution_code = rec[1]
                                institution_shortname = rec[2]
                                course_code = rec[3]
                                course_name = rec[7]
                                start_year = rec[8]

                                # check if this appn is already in the record
                                newappn = True
                                for appn in student.data['applications']:
                                    if appn.get('institution_code',"") == institution_code and appn.get('course_code',"") == course_code and appn.get('start_year',"") == start_year:
                                        newappn = False

                                # if this appn is not in the record yet, add it
                                if newappn:
                                    student.data['applications'].append({
                                        "institution_code": institution_code,
                                        "institution_shortname": institution_shortname,
                                        "course_code": course_code,
                                        "course_name": course_name,
                                        "start_year": start_year
                                    })
                            except:
                                # failed to add the appn data to the student
                                failures.append('Failed to read what appeared to be application data out of row ' + str(counter))
                        else:
                            # there was no student for this appn, what to do?
                            failures.append('There did not appear to be a record to append the application data from row ' + str(counter) + ' to')
                            
                flash('Processed ' + str(counter) + ' rows of data')
                return render_template('swap/admin/import.html', model=model, failures=failures, updates=updates)


            elif model.lower() == 'course':
                klass = getattr(models, model[0].capitalize() + model[1:] )
                klass().delete_all()
                for rec in records:
                    r = klass()
                    if rec.get('previous_name',"") != "":
                        rec['previous_name'] = rec['previous_name'].split(',')
                    else:
                        rec['previous_name'] = []
                    r.data = rec
                    r.save()

            else:
                klass = getattr(models, model[0].capitalize() + model[1:] )
                klass().delete_all()
                klass().bulk(records)
            
            time.sleep(1)
            checklen = klass.query(q="*")['hits']['total']
            
            flash(str(len(records)) + " records have been imported, there are now " + str(checklen) + " records.")
            return render_template('swap/admin/import.html', model=model)

        except:
            flash("There was an error importing your records. Please try again.")
            return render_template('swap/admin/import.html', model=model)



