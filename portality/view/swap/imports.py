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
    return newstr.strip()


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
            what = request.form['exportwhat']
            if what == 'applications':
                uni = request.form['appnsuniversity']
            else:
                uni = request.form['progsuniversity']
            
            students = _get_students(uni,what)
            return _download_applications(students, what, uni)

        else:
            try:
                records = []
                if "csv" in request.files.get('upfile').filename:
                    upfile = request.files.get('upfile')
                    if model.lower() == 'ucas' or model.lower() == 'asr':
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


                if model.lower() == 'asr': # this is the final data upload
                    updates = []
                    failures = []
                    for rec in records:
                        if rec[0].strip().lower() != 'surname':
                            try:
                                # these records should only exist for students with ucas numbers already in system, so only match by that
                                qry = { 'query': { 'bool': { 'must': [] } }, 'sort': {'created_date.exact': 'desc'} }
                                qry['query']['bool']['must'].append({'term':{'ucas_number'+app.config['FACET_FIELD']:rec[4].strip()}})
                                q = models.Student().query(q=qry)
                                if q.get('hits',{}).get('total',0) == 1:
                                    sid = q['hits']['hits'][0]['_source']['id']
                                    student = models.Student.pull(sid)
                                    nofaps = []
                                    for ap in student.data['applications']:
                                        if ap['choice_number'] != 'Final':
                                            nofaps.append(ap)
                                    student.data['applications'] = nofaps
                                    student.data['applications'].append({
                                        "choice_number": 'Final',
                                        "institution_code": rec[9].strip(),
                                        "institution_shortname": rec[8].strip(),
                                        "course_code": rec[10].strip(),
                                        "decisions": "Not placed" if rec[12].strip().lower == "not placed" else "",
                                        "course_name": "" if rec[12].strip().strip().lower == "not placed" else rec[12].strip(),
                                        "start_year": rec[14].strip()
                                    })
                                    student.save()
                                    updates.append('Updated student <a href="/admin/student/' + student.id + '">' + student.data['first_name'] + ' ' + student.data['last_name'] + '</a>')
                                else:
                                    failures.append('Could not find student in system with UCAS number ' + rec[4])
                            except:
                                failures.append('Failed to read student data for ' + rec[4])

                    flash('Processed data')
                    return render_template('swap/admin/import.html', model=model, failures=failures, updates=updates)



                elif model.lower() == 'ucas': # this is the main student applications, may also be referred to as ASR, but is not the ASR final data
                    previous = None
                    addun = False
                    appnset = []
                    counter = 0
                    updates = []
                    failures = []
                    stayedsame = []
                    for rec in records:
                        counter += 1
                        if rec[0].strip().lower() != 'surname':
                            try:
                                date_of_birth = rec[2].strip()
                                if ' ' in date_of_birth:
                                    parts = date_of_birth.split(' ')
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
                                student = None
                                qry = { 'query': { 'bool': { 'must': [] } }, 'sort': {'created_date.exact': 'desc'} }
                                if len(rec[3]) > 1: # run query with ucas number search if available
                                    qry['query']['bool']['must'].append({'term':{'ucas_number'+app.config['FACET_FIELD']:rec[3].strip()}})
                                    q = models.Student().query(q=qry)
                                    if q.get('hits',{}).get('total',0) == 1:
                                        sid = q['hits']['hits'][0]['_source']['id']
                                        student = models.Student.pull(sid)
                                # if ucas number did not find it try with names and dob
                                if student is None and len(rec[0]) > 1 and len(rec[1]) > 1 and len(date_of_birth) > 1:
                                    qry['query']['bool']['must'] = []
                                    qry['query']['bool']['must'].append({'match':{'last_name':{'query':rec[0].strip(), 'fuzziness':0.8}}})
                                    qry['query']['bool']['must'].append({'match':{'first_name':{'query':rec[1].strip().split(' ')[0], 'fuzziness':0.8}}})
                                    qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:date_of_birth}})
                                    q = models.Student().query(q=qry)
                                    if q.get('hits',{}).get('total',0) != 0:
                                        sid = q['hits']['hits'][0]['_source']['id']
                                        student = models.Student.pull(sid)

                                # what is group = rec[4] needed for? Does not match to old values
                                nappn = {
                                    "choice_number": rec[7].strip(),
                                    "institution_shortname": rec[8].strip(),
                                    "institution_code": rec[9].strip(),
                                    "course_code": rec[10].strip(),
                                    "course_name": rec[11].strip(),
                                    "decisions": rec[15].strip(),
                                    "conditions": rec[17].strip(),
                                    "start_year": rec[21].strip()
                                }

                                if previous is not None and (student is None or previous.id != student.id or counter == len(records)):
                                    if counter == len(records):
                                        appnset.append(nappn) # make sure to catch the last one
                                    oldappns = previous.data.get('applications',[])
                                    changed = len(oldappns) != len(appnset) or any(x != y for x, y in zip(oldappns,appnset))
                                    if changed or addun:
                                        if addun:
                                            addun = False
                                            updates.append('Updated student <a href="/admin/student/' + previous.id + '">' + previous.data['first_name'] + ' ' + previous.data['last_name'] + '</a> with UCAS number ' + previous.data['ucas_number'])
                                        if changed:
                                            previous.data['applications'] = appnset
                                            updates.append('Updated student <a href="/admin/student/' + previous.id + '">' + previous.data['first_name'] + ' ' + previous.data['last_name'] + '</a>')
                                        previous.save()
                                    else:
                                        stayedsame.append('Found <a href="/admin/student/' + previous.id + '">' + previous.data['first_name'] + ' ' + previous.data['last_name'] + '</a> - no change.')
                                    appnset = []
                                    previous = None

                                if student is None:
                                    failures.append('Failed to find student ' + rec[1] + ' ' + rec[0] + ' (' + rec[3] + ') from row ' + str(counter))
                                    appnset = []
                                
                                if previous is None or student is None or previous.id != student.id:
                                    previous = student
                                    if previous is not None and len(rec[3]) > 1 and not previous.data.get('ucas_number',False):
                                        previous.data['ucas_number'] = rec[3].strip()
                                        addun = True
                                student = None
                                appnset.append(nappn)
                            except:
                                # failed to add the appn data to the student
                                failures.append('Failed to read what appeared to be application data out of row ' + str(counter))
                                
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
                            qry['query']['bool']['must'] = []
                            # archive search
                            if len(rc.get('archive',"")) > 1:
                                qry['query']['bool']['must'].append({'term':{'archive'+app.config['FACET_FIELD']:rc['archive']}})
                            if len(rc.get('last_name',"")) > 1 and len(rc.get('first_name',"")) > 1:
                                qry['query']['bool']['must'].append({'match':{'last_name':{'query':rc['last_name'], 'fuzziness':0.9}}})
                                qry['query']['bool']['must'].append({'match':{'first_name':{'query':rc['first_name'], 'fuzziness':0.9}}})
                            q = models.Student().query(q=qry)
                            if q.get('hits',{}).get('total',0) > 1:
                                if len(rc.get('date_of_birth',"")) > 1:
                                    # tidy the date of birth and test for EN/US format, then narrow the search
                                    # convert date of birth format if necessary
                                    try:
                                        dob = rc['date_of_birth']
                                        if '-' in date_of_birth: dob = dob.replace('-','/')
                                        parts = date_of_birth.split('/')
                                        tryflip = True
                                        if parts[1] > 12:
                                            parts = [parts[1],parts[0],parts[2]]
                                            tryflip = False
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
                                else:
                                    q = {}
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





                elif model.lower() == 'college_progression':
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
                        rec = {k.replace(" ",""): v for k,v in rec.items()}
                        # look for the student in the index
                        counter += 1
                        student = None
                        try:
                            qry['query']['bool']['must'] = [] #{'term':{'archive'+app.config['FACET_FIELD']:'current'}}
                            qry['query']['bool']['must'].append({'match':{'last_name':{'query':rec['last_name'], 'fuzziness':0.9}}})
                            qry['query']['bool']['must'].append({'match':{'first_name':{'query':rec['first_name'], 'fuzziness':0.9}}})
                            qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:rec['date_of_birth']}})
                            if len(rec.get('archive',"")) > 1:
                                qry['query']['bool']['must'].append({'term':{'archive'+app.config['FACET_FIELD']:rec['archive']}})
                            q = models.Student().query(q=qry)
                            sid = q['hits']['hits'][0]['_source']['id']
                            student = models.Student.pull(sid)
                        except:
                            failures.append('Could not find student ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' on row ' + str(counter) + ' in the system.')

                        if student is not None:
                            try:
                                progn = {
                                    'access_course': rec.get('access_course',''),
                                    'progress_where': rec.get('progress_where',''),
                                    'campus': rec.get('campus',''),
                                    'course_name': rec.get('course_name',''),
                                    'reg_1st_year': rec.get('reg_1st_year',''),
                                    '1st_year_result': rec.get('1st_year_result',''),
                                    'reg_2nd_year': rec.get('reg_2nd_year',''),
                                    '2nd_year_result': rec.get('2nd_year_result',''),
                                    'progression_to_university': rec.get('progression_to_university','')
                                }

                                which = False
                                if 'college_progressions' not in student.data: student.data['college_progressions'] = []
                                if len(student.data['college_progressions']) > 0:
                                    c = 0
                                    for prog in student.data['college_progressions']:
                                        if prog['progress_where'] == progn['progress_where'] and prog['course_name'] == progn['course_name']:
                                            which = c
                                        c += 1
                                
                                if isinstance(which,bool):
                                    student.data['college_progressions'].append(progn)
                                else:
                                    student.data['college_progressions'][which] = progn
                                student.save()
                                updates.append('Saved student ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' college progression data.')
                            except:
                                failures.append('Failed to save student ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' college progression data.')

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
                                ]
                            }
                        }
                    }
                    for rec in records:
                        rec = {k.replace(" ",""): v for k,v in rec.items()}
                        # look for the student in the index
                        counter += 1
                        student = None
                        try:
                            qry['query']['bool']['must'] = [] #{'term':{'archive'+app.config['FACET_FIELD']:'current'}}
                            if len(rec.get('ucas_number',"")) > 1:
                                qry['query']['bool']['must'].append({'term':{'ucas_number'+app.config['FACET_FIELD']:rec['ucas_number']}})
                            elif len(rec.get('last_name',"")) > 1 and len(rec.get('date_of_birth',"")) > 1 and len(rec.get('first_name',"")) > 1:
                                qry['query']['bool']['must'].append({'match':{'last_name':{'query':rec['last_name'], 'fuzziness':0.9}}})
                                qry['query']['bool']['must'].append({'match':{'first_name':{'query':rec['first_name'], 'fuzziness':0.9}}})
                                qry['query']['bool']['must'].append({'term':{'date_of_birth'+app.config['FACET_FIELD']:rec['date_of_birth']}})
                            if len(qry['query']['bool']['must']) != 0:
                                if len(rec.get('archive',"")) > 1:
                                    qry['query']['bool']['must'].append({'term':{'archive'+app.config['FACET_FIELD']:rec['archive']}})
                                q = models.Student().query(q=qry)
                                sid = q['hits']['hits'][0]['_source']['id']
                                student = models.Student.pull(sid)
                        except:
                            failures.append('Could not find student ' + rec.get('first_name',"") + " " + rec.get('last_name',"") + ' on row ' + str(counter) + ' in the system.')

                        if student is not None:
                            try:
                                # this is missing initial uni decision, initial student decision, final uni decision
                                progn = {
                                    'starting_year': rec.get('start_year',rec.get('starting_year','')),
                                    'course_name': rec.get('course_name',''),
                                    'course_code': rec.get('course_code',''),
                                    'institution_shortname': rec.get('institution_shortname',''),
                                    'decisions': rec.get('decisions',''),
                                    'reg_1st_year': rec.get('reg_1st_year',''),
                                    '1st_year_result': rec.get('1st_year_result',''),
                                    'reg_2nd_year': rec.get('reg_2nd_year',''),
                                    '2nd_year_result': rec.get('2nd_year_result',''),
                                    'reg_3rd_year': rec.get('reg_3rd_year',''),
                                    '3rd_year_result': rec.get('3rd_year_result',''),
                                    'reg_4th_year': rec.get('reg_4th_year',rec.get('reg_4th_year_or_left','')),
                                    'degree_classification_awarded': rec.get('degree_classification_awarded','')
                                }
                                
                                which = False
                                if 'progressions' not in student.data: student.data['progressions'] = []
                                if len(student.data['progressions']) > 0:
                                    c = 0
                                    for prog in student.data['progressions']:
                                        if prog['institution_shortname'] == progn['institution_shortname'] and prog['course_name'] == progn['course_name']:
                                            which = c
                                        c += 1
                                
                                if len(progn['institution_shortname']) > 0:
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

            except:
                flash("There was an error importing your records. Please try again.")
                return render_template('swap/admin/import.html', model=model)



def _get_students(institution,whatsort):
    qry = {
        'query':{
            'bool':{
                'must':[
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


