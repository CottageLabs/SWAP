import json, csv, time, string
import cStringIO as StringIO
from datetime import datetime

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect, send_file
from flask.ext.login import current_user

from portality.core import app
import portality.models as models
from portality.view.swap.forms import dropdowns as dropdowns


blueprint = Blueprint('imports', __name__)


def clean(strn):
    newstr = ''
    allowed = string.lowercase + string.uppercase + "@!%&*()_-+=;:~#./?[]{}, '" + '0123456789'
    for part in strn:
        if part == '\n':
            newstr += '  '
        elif part in allowed:
            newstr += part
    return newstr


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
        if model == 'university':
            appn_unis = dropdowns('student','applications.institution_shortname')
            prog_unis = dropdowns('student','progressions.institution_shortname')
        else:
            appn_unis = []
            prog_unis = []
        return render_template('swap/admin/import.html', model=model, appn_unis=appn_unis, prog_unis=prog_unis)
    elif request.method == 'POST':
        # check if it is a submission request from the university import page
        # for an export of university progressions
        if request.form['submit'] == 'Export the university list':
            uni = request.form['exportuniversity']
            what = request.form['exportwhat']
            
            students = _get_students(uni,what)
            return _download_applications(students, what, uni)


        else:
    
            if 1==1:
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
                    # start with no student and an empty applications list
                    student = None
                    appnset = []
                    
                    # iterate each row in the csv, which has header rows of student 
                    # data followed by multiple rows of student applications
                    counter = 0
                    failures = []
                    updates = []
                    stayedsame = []
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
                        

                        if probappn:
                            # there should be a student already in this case
                            if student is not None:
                                try:
                                    # get the appn data from the rows - 0 is column A of spreadsheet
                                    choice_number = rec[0]
                                    institution_code = rec[1]
                                    institution_shortname = rec[2]
                                    course_code = rec[3]
                                    decisions = rec[5]
                                    conditions = rec[6]
                                    course_name = rec[7]
                                    start_year = rec[8]


                                    appnset.append({
                                        "choice_number": choice_number,
                                        "institution_code": institution_code,
                                        "institution_shortname": institution_shortname,
                                        "course_code": course_code,
                                        "decisions": decisions,
                                        "conditions": conditions,
                                        "course_name": course_name,
                                        "start_year": start_year
                                    })
                                                                        
                                except:
                                    # failed to add the appn data to the student
                                    failures.append('Failed to read what appeared to be application data out of row ' + str(counter))

                        elif probperson:
                            # when hitting a person row, save the previous person
                            # if there was one, then reset back to none
                            if student is not None:
                                # TODO: test if appnset is different from apps for person
                                oldappns = student.data.get('applications',[])
                                if len(oldappns) != len(appnset):
                                    changed = True
                                else:
                                    check = zip(oldappns,appnset)
                                    changed = any(x != y for x, y in check)
                                if changed:
                                    student.data['applications'] = appnset
                                    student.save()
                                    updates.append('Updated student <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a>')
                                else:
                                    stayedsame.append('Found <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a> - no change.')
                                student = None
                                appnset = []

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
                                    
                                    if len(str(parts[0])) == 1:
                                        parts[0] = '0' + str(parts[0])
                                    if len(str(mon)) == 1:
                                        mon = '0' + str(mon)
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
                                                '''{'term':
                                                    {'archive'+app.config['FACET_FIELD']:'current'}
                                                }'''
                                            ]
                                        }
                                    }
                                }

                                # run query with ucas number search if available
                                if len(ucas_number) > 1:
                                    qry['query']['bool']['must'].append({'term':{'ucas_number'+app.config['FACET_FIELD']:ucas_number}})
                                    q = models.Student().query(q=qry)
                                    if q.get('hits',{}).get('total',0) == 1:
                                        sid = q['hits']['hits'][0]['_source']['id']
                                        student = models.Student.pull(sid)
                                    
                                # if ucas number did not find it,
                                # use combinations of first part of firstname, lastname, dob and postcode
                                fnqry = {'match':{'first_name':{'query':first_name.split(' ')[0], 'fuzziness':0.8}}}
                                lnqry = {'match':{'last_name':{'query':last_name, 'fuzziness':0.8}}}
                                dobqry = {'term':{'date_of_birth'+app.config['FACET_FIELD']:date_of_birth}}
                                pcqry = [
                                    {'match':{'post_code':{'query':post_code, 'operator': 'and', 'fuzziness':0.9}}},
                                    {'term':{'post_code'+app.config['FACET_FIELD']:post_code.replace(' ','')}},
                                    {'term':{'post_code'+app.config['FACET_FIELD']:post_code.replace(' ','').lower()}}
                                ]
                                
                                if student is None:
                                    qry['query']['bool']['must'] = []
                                    if len(last_name) > 1:
                                        qry['query']['bool']['must'].append(lnqry)
                                    if len(first_name) > 1:
                                        qry['query']['bool']['must'].append(fnqry)
                                    if len(date_of_birth) > 1:
                                        qry['query']['bool']['must'].append(dobqry)
                                    if len(post_code) > 1:
                                        qry['query']['bool']['should'] = pcqry
                                        qry['query']['bool']['minimum_should_match'] = 1

                                    q = models.Student().query(q=qry)
                                    if q.get('hits',{}).get('total',0) == 1:
                                        sid = q['hits']['hits'][0]['_source']['id']
                                        student = models.Student.pull(sid)
                                if last_name == 'Whatley':
                                    print qry
                                    print student
                                # if still not found, ignore the dob
                                if student is None:
                                    qry['query']['bool']['must'] = []
                                    if len(last_name) > 1:
                                        qry['query']['bool']['must'].append(lnqry)
                                    if len(first_name) > 1:
                                        qry['query']['bool']['must'].append(fnqry)

                                    q = models.Student().query(q=qry)
                                    if q.get('hits',{}).get('total',0) == 1:
                                        sid = q['hits']['hits'][0]['_source']['id']
                                        student = models.Student.pull(sid)

                                # if still not found, ignore the post code
                                if student is None:
                                    qry['query']['bool']['must'] = []
                                    if 'should' in qry['query']['bool'].keys():
                                        del qry['query']['bool']['should']
                                        del qry['query']['bool']['minimum_should_match']
                                    if len(last_name) > 1:
                                        qry['query']['bool']['must'].append(lnqry)
                                    if len(first_name) > 1:
                                        qry['query']['bool']['must'].append(fnqry)
                                    if len(date_of_birth) > 1:
                                        qry['query']['bool']['must'].append(dobqry)

                                    q = models.Student().query(q=qry)
                                    if q.get('hits',{}).get('total',0) == 1:
                                        sid = q['hits']['hits'][0]['_source']['id']
                                        student = models.Student.pull(sid)

                                # if still not found, try only first and last name
                                if student is None:
                                    qry['query']['bool']['must'] = []
                                    if len(last_name) > 1:
                                        qry['query']['bool']['must'].append(lnqry)
                                    if len(first_name) > 1:
                                        qry['query']['bool']['must'].append(fnqry)

                                    q = models.Student().query(q=qry)
                                    if q.get('hits',{}).get('total',0) == 1:
                                        sid = q['hits']['hits'][0]['_source']['id']
                                        student = models.Student.pull(sid)

                                # if no student found, write a failure note
                                if student is None and counter > 2:
                                    failures.append('Could not find a record in the system for ' + first_name + ' ' + last_name + ' in row ' + str(counter))

                                # if a student is found, and a ucas number is available, update the student record with it
                                if student is not None and len(ucas_number) > 1:
                                    if not len(student.data.get('ucas_number',"")) > 1:
                                        student.data['ucas_number'] = ucas_number
                                        student.save()
                                        updates.append('Updated student <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a> with UCAS number ' + ucas_number)
                                
                            except:
                                # failed to read the person row - except top 2 rows are always info header rows
                                if counter > 2:
                                    failures.append('Failed to read what appeared to be person details out of row ' + str(counter))

                        else:
                            # there was no student for this appn, what to do?
                            failures.append('There did not appear to be a student record to append the application data from row ' + str(counter) + ' to')
                                
                                
                        # if this is the last line of the file, save any remaining student
                        if counter == len(records):
                            try:
                                if student is not None:
                                    oldappns = student.data.get('applications',[])
                                    if len(oldappns) != len(appnset):
                                        changed = True
                                    else:
                                        check = zip(oldappns,appnset)
                                        changed = any(x != y for x, y in check)
                                    if changed:
                                        student.data['applications'] = appnset
                                        student.save()
                                        updates.append('Updated student <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a>')
                                    else:
                                        stayedsame.append('Found <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a> - no change.')
                                    student = None
                                    appnset = []                                
                            except:
                                pass

                    flash('Processed ' + str(counter) + ' rows of data')
                    return render_template('swap/admin/import.html', model=model, failures=failures, updates=updates, stayedsame=stayedsame)


                
                
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




                elif model.lower() == 'college':
                    failures = []
                    updates = []
                    counter = 0
                    # query the student index for a matching student
                    qry = {
                        'query':{
                            'bool':{
                                'must':[
                                ]
                            }
                        }
                    }
                    for rec in records:
                        rc = {}
                        for k in rec:
                            rc[k.lower().strip()] = rec[k]
                        # look for the student in the index
                        counter += 1
                        student = None
                        try:
                            qry['query']['bool']['must'] = [] #{'term':{'archive'+app.config['FACET_FIELD']:'current'}}
                            if len(rc.get('last_name',"")) > 1:
                                qry['query']['bool']['must'].append({'match':{'last_name':{'query':rc['last_name'], 'fuzziness':0.8}}})
                            if len(rc.get('first_name',"")) > 1:
                                qry['query']['bool']['must'].append({'match':{'first_name':{'query':rc['first_name'], 'fuzziness':0.8}}})
                            q = models.Student().query(q=qry)
                            if q.get('hits',{}).get('total',0) > 1 and len(rc.get('date_of_birth',"")) > 1:
                                # tidy the date of birth and test for EN/US format, then narrow the search
                                # convert date of birth format if necessary
                                try:
                                    dob = rc['date_of_birth']
                                    if '-' in date_of_birth: dob = dob.replace('-','/')
                                    parts = date_of_birth.split('/')
                                    tryflip = true
                                    if parts[1] > 12:
                                        parts = [parts[1],parts[0],parts[2]]
                                        tryflip = false
                                    if len(str(parts[2])) == 2:
                                        if parts[2] > 50:
                                            parts[2] = str("19" + str(parts[2]))
                                        else:
                                            parts[2] = str("20" + str(parts[2]))    
                                    dob = str(parts[0]) + '/' + str(parts[1]) + '/' + str(parts[2])
                                    qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:dob}})
                                    q = models.Student().query(q=qry)
                                    if  q.get('hits',{}).get('total',0) == 0 and tryflip:
                                        dob = str(parts[1]) + '/' + str(parts[0]) + '/' + str(parts[2])
                                        del qry['query']['bool']['must'][-1]
                                        qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:dob}})
                                        q = models.Student().query(q=qry)
                                except:
                                    pass
                            sid = q['hits']['hits'][0]['_source']['id']
                            student = models.Student.pull(sid)
                        except:
                            failures.append('Could not find student ' + rc.get('first_name',"") + " " + rc.get('last_name',"") + ' on row ' + str(counter) + ' in the system.')

                        if student is not None:
                            try:
                                student.data['completedunits'] = rc.get('completedunits','')
                                student.data['profilegrades'] = rc.get('profilegrades','')
                                student.data['courseexit'] = rc.get('courseexit','')
                                student.data['exitreason'] = rc.get('exitreason','')
                                student.data['progress'] = rc.get('progress','')
                                student.data['progresswhere'] = rc.get('progresswhere','')
                                student.save()
                                updates.append('Saved student ' + rc.get('first_name',"") + " " + rc.get('last_name',"") + ' progression data.')
                            except:
                                failures.append('Failed to save student ' + rc.get('first_name',"") + " " + rc.get('last_name',"") + ' progression data.')

                    flash('Processed ' + str(counter) + ' rows of data')
                    return render_template('swap/admin/import.html', model=model, failures=failures, updates=updates)





                elif model.lower() == 'university':
                    failures = []
                    updates = []
                    counter = 0
                    # query the student index for a matching student
                    qry = {
                        'query':{
                            'bool':{
                                'must':[
                                    '''{'term':
                                        {'archive'+app.config['FACET_FIELD']:'current'}
                                    }'''
                                ]
                            }
                        }
                    }
                    for rec in records:
                        # look for the student in the index
                        counter += 1
                        student = None
                        try:
                            qry['query']['bool']['must'] = [] #{'term':{'archive'+app.config['FACET_FIELD']:'current'}}
                            if len(rec.get('ucas_number',"")) > 1:
                                qry['query']['bool']['must'].append({'term':{'ucas_number'+app.config['FACET_FIELD']:rec['ucas_number']}})
                            else:
                                if len(rec.get('last_name',"")) > 1:
                                    qry['query']['bool']['must'].append({'match':{'last_name':{'query':rec['last_name'], 'fuzziness':0.8}}})
                                if len(rec.get('first_name',"")) > 1:
                                    qry['query']['bool']['must'].append({'match':{'first_name':{'query':rec['first_name'], 'fuzziness':0.8}}})
                                if len(rec.get('date_of_birth',"")) > 1:
                                    qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:rec['date_of_birth']}})
                            q = models.Student().query(q=qry)
                            sid = q['hits']['hits'][0]['_source']['id']
                            student = models.Student.pull(sid)
                        except:
                            failures.append('Could not find student ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' on row ' + str(counter) + ' in the system.')

                        if student is not None:
                            try:
                                # this is missing initial uni decision, initial student decision, final uni decision
                                progn = {
                                    'start_year': rec.get('start_year',''),
                                    'course_name': rec.get('course_name',''),
                                    'course_code': rec.get('course_code',''),
                                    'institution_shortname': rec.get('institution_shortname',''),
                                    'decisions': rec.get('decisions',''),
                                    'reg_1st_year': rec.get('reg_1st_year',''),
                                    'reg_2nd_year_or_left': rec.get('reg_2nd_year_or_left',''),
                                    'reg_3rd_year_or_left': rec.get('reg_3rd_year_or_left',''),
                                    'reg_4th_year_or_left': rec.get('reg_4th_year_or_left',''),
                                    'degree_classification_awarded': rec.get('degree_classification_awarded','')
                                }
                                
                                which = False
                                if 'progressions' not in student.data: student.data['progressions'] = []
                                if len(student.data['progressions']) > 0:
                                    c = 0
                                    for prog in student.data['progressions']:
                                        if prog['institution_shortname'] == progn['institution_shortname'] and prog['course_code'] == progn['course_code']:
                                            which = c
                                        c += 1
                                
                                if len(progn['course_code']) > 0 and len(progn['institution_shortname']) > 0:
                                    if isinstance(which,bool):
                                        student.data['progressions'].append(progn)
                                    else:
                                        student.data['progressions'][which] = progn

                                    student.save()
                                    updates.append('Saved student ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' progression data.')
                                else:
                                    failures.append('Blank course code or institution shortname for ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' progression data, so did not save this row.')
                            except:
                                failures.append('Failed to save student ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' progression data.')

                    flash('Processed ' + str(counter) + ' rows of data')
                    return render_template('swap/admin/import.html', model=model, failures=failures, updates=updates)


                elif model.lower() == 'progression':
                    if request.values.get('overwrite',False):
                        models.Progression().delete_all()
                        flash('Deleted all previous progression records.')
                    if request.values.get('overwrite_east',False):
                        models.Progression().delete_east()
                        flash('Deleted all previous East progression records.')
                    if request.values.get('overwrite_west',False):
                        models.Progression().delete_west()
                        flash('Deleted all previous West progression records.')
                    new = 0
                    updates = 0
                    deletes = 0
                    counter = 0
                    for rec in records:
                        counter += 1
                        prog = None
                        rid = None
                        if 'SWAP_ID' in rec:
                            rid = rec['SWAP_ID']
                            del rec['SWAP_ID']
                        elif 'swap_id' in rec:
                            rid = rec['swap_id']
                            del rec['swap_id']
                        if rid is not None: prog = models.Progression.pull(rid)
                        if prog is None:
                            new += 1
                            prog = models.Progression()
                            if 'swap_delete' in rec: del rec['swap_delete']
                            for k in rec.keys():
                                prog[k] = clean(rec[k])
                            prog.save()
                        else:
                            deleteit = False
                            if 'swap_delete' in rec:
                                if rec['swap_delete'].lower() == 'delete': deleteit = True
                                del rec['swap_delete']
                            if deleteit:
                                deletes += 1
                                prog.delete()
                            else:
                                updates += 1
                                for k in rec.keys():
                                    prog[k] = clean(rec[k])
                                prog.data['id'] = rid
                                prog.save()

                    flash('Processed ' + str(counter) + ' rows of progression records, updated ' + str(updates) + ' records, created ' + str(new) + ' new records, deleted ' + str(deletes) + ' records')
                    return render_template('swap/admin/import.html', model=model)


                else:
                    klass = getattr(models, model[0].capitalize() + model[1:] )
                    klass().delete_all()
                    klass().bulk(records)
                
                time.sleep(1)
                checklen = klass.query(q="*")['hits']['total']
                
                flash(str(len(records)) + " records have been imported, there are now " + str(checklen) + " records.")
                return render_template('swap/admin/import.html', model=model)

            else: # should be an exception handler
                flash("There was an error importing your records. Please try again.")
                return render_template('swap/admin/import.html', model=model)



def _get_students(institution,whatsort):
    qry = {
        'query':{
            'bool':{
                'must':[
                    '''{'term':
                        {'archive'+app.config['FACET_FIELD']:'current'}
                    }'''
                ]
            }
        },
        "sort":[{"created_date"+app.config['FACET_FIELD']:{"order":"desc"}}],
        'size':10000
    }
    if not isinstance(institution,bool):
        if whatsort == 'applications':
            qry['query']['bool']['must'].append({'term':{'archive'+app.config['FACET_FIELD']:'current'}})
            qry['query']['bool']['must'].append({'term':{'applications.institution_shortname'+app.config['FACET_FIELD']:institution}})
        else:
            qry['query']['bool']['must'].append({'term':{'progressions.institution_shortname'+app.config['FACET_FIELD']:institution}})

    q = models.Student().query(q=qry)
    students = [i['_source'] for i in q.get('hits',{}).get('hits',[])]
    matchedstudents = []
    for student in students:
        allowedapps = []
        if whatsort == 'applications':
            apps = student['applications']
        else:
            apps = student['progressions']
        for appn in apps:
            if not isinstance(institution,bool):
                if appn['institution_shortname'] == institution:
                    allowedapps.append(appn)
            else:
                allowedapps.append(appn)
        if len(allowedapps) > 0:
            if whatsort == 'applications':
                student['applications'] = allowedapps
            else:
                student['progressions'] = allowedapps
            matchedstudents.append(student)
    return matchedstudents





def _download_applications(recordlist, whatsort, uni):

    keys = ['start_year','locale','ucas_number','last_name','first_name','gender','date_of_birth','post_code','college','institution_shortname', 'course_name','course_code','decisions','reg_1st_year','reg_2nd_year_or_left','reg_3rd_year_or_left','reg_4th_year_or_left','degree_classification_awarded']

    # make a csv string of the records, with one line per application
    csvdata = StringIO.StringIO()
    firstrecord = True
    for record in recordlist:
        if whatsort == 'applications':
            listing = record.get('applications',[])
        else:
            listing = record.get('progressions',[])
        for appn in listing:
            # extend the appn with the record data
            appn.update(record)
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
            # and then add each application for each student as a line
            firstkey = True
            for key in keys:
                if firstkey:
                    firstkey = False
                else:
                    csvdata.write(',')
                if key in appn.keys():
                    # process each key as required
                    tidykey = appn[key].replace('"',"'")
                    csvdata.write('"' + tidykey + '"')
                else:
                    csvdata.write('""')

    # dump to the browser as a csv attachment
    csvdata.seek(0)
    return send_file(
        csvdata, 
        mimetype='text/csv',
         attachment_filename="swap_" + uni + "_export_" + datetime.now().strftime("%d%m%Y%H%M") + ".csv",
        as_attachment=True
    )


