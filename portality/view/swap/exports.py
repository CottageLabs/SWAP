
from datetime import datetime

import cStringIO as StringIO
import string

import json

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect, send_file
from flask.ext.login import current_user

from portality.core import app
import portality.models as models


blueprint = Blueprint('reports', __name__)


# restrict everything in exports to logged in users who can view admin
@blueprint.before_request
def restrict():
    if current_user.is_anonymous():
        return redirect('/account/login?next=' + request.path)
    elif not current_user.view_admin:
        abort(401)



@blueprint.route('/', methods=['GET','POST'])
def index():
    query = json.loads(request.values.get('q','{"query":{"match_all":{}}}'))
    selected = json.loads(request.values.get('selected','[]'))

    if request.method == 'GET':
        return render_template('swap/exports/index.html', query=json.dumps(query), selected=json.dumps(selected))

    elif request.method == 'POST':
        keys = request.form.keys()
        if 'applications_UF' in keys:
            if 'bool' not in query['query'].keys(): query['query'] = {'bool':{'should':[]}}
            if 'should' not in query['query']['bool'].keys(): query['query']['bool']['should'] = []
            query['query']['bool']['should'].append({'term':{'applications.decisions.exact':'UF'}})
            query['query']['bool']['should'].append({'term':{'applications.choice_number.exact':'Final'}})
        s = models.Student.query(q=query)
        students = []
        for i in s.get('hits',{}).get('hits',[]): 
            if len(selected) == 0 or i['_source']['id'] in selected:
                students.append(i['_source'])
        
        keys = [ i for i in keys if i not in ['query','submit','selected']]
        
        return download_csv(students,keys)


def fixify(strng,unquote=True):
    if isinstance(strng, (int, long)):
        return str(strng)
    else:
        newstr = ''
        allowed = string.lowercase + string.uppercase + "@!%&*()_-+=;:~#./?[]{}, '" + '0123456789'
        for part in strng:
            if part == '"':
                if unquote:
                    newstr += "'"
                else:
                    newstr += part
            elif part in allowed or part == '\n':
                newstr += part
        return newstr


def download_csv(recordlist,keys):
    if 'applications_UF' in keys:
        keys.remove('applications_UF')
        applications_UF = True
    else:
        applications_UF = False
    
    # re-order some of the keys
    keyorder = ['first_name','last_name','date_of_birth', 'gender','college','campus','course','travel','email','home_phone','mobile_phone','address','post_code','nationality']

    for k in reversed(keyorder):
        if k in keys:
            keys.remove(k)
            keys = [k] + keys

    progressionkeys = ['starting_year','course_name','course_code','institution_shortname','decisions','reg_1st_year','1st_year_result','reg_2nd_year','2nd_year_result','reg_3rd_year','3rd_year_result','reg_4th_year','degree_classification_awarded']
    if 'uniprogression' in keys:
        keys.remove('uniprogression')
        for ky in progressionkeys:
            keys.append(ky)

    if 'mentoring' in keys:
        i = keys.index('mentoring') + 1
        keys.insert(i,'mentorrequest')
        keys.insert(i,'mentoroffer')
        keys.insert(i,'mentortraining1')
        keys.insert(i,'mentortraining2')
        keys.insert(i,'mentortraining3')
        keys.insert(i,'mentornotes')
        keys.remove('mentoring')

    if 'progression' in keys:
        i = keys.index('progression') + 1
        keys.insert(i,'completedunits')
        keys.insert(i,'profilegrades')
        keys.insert(i,'courseexit')
        keys.insert(i,'exitreason')
        keys.insert(i,'progress')
        keys.insert(i,'progresswhere')
        keys.remove('progression')
    
    if 'withdrawn' in keys:
        i = keys.index('withdrawn') + 1
        keys.insert(i,'exitreason')
        keys.insert(i,'courseexit')
        
    if 'date_of_birth' in keys:
        i = keys.index('date_of_birth') + 1
        keys.insert(i,'ageonentry')

    if 'applications' in keys:
        i = keys.index('applications') + 1
        keys.insert(i,'applications_info')
        keys.insert(i,'applications_course')

    if 'school_qualifications' in keys:
        i = keys.index('school_qualifications') + 1
        keys.insert(i,'school_qualifications_levels')

    if 'post_school_qualifications' in keys:
        i = keys.index('post_school_qualifications') + 1
        keys.insert(i,'post_school_qualifications_levels')

    # make a csv string of the records
    csvdata = StringIO.StringIO()
    firstrecord = True
    for record in recordlist:
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
            unquote = True
            if firstkey:
                firstkey = False
            elif key not in ['applications_info','applications_course','school_qualifications_levels','post_school_qualifications_levels']:
                csvdata.write(',')
            if key in record.keys() or key == 'address' or key in progressionkeys:
                if key == 'address':
                    tidykey = record.get('address_line_1','') + '\n'
                    if record.get('address_line_2',''):
                        tidykey += record['address_line_2']
                    tidykey += record.get('city','')
                    tidykey = tidykey.replace('"',"'")
                elif key == 'applications':
                    unquote = False
                    au = ''
                    ac = ''
                    ai = ''
                    firstline = True
                    for line in record[key]:
                        #if ( applications_UF and 'UF' in line['decisions'] ) or (applications_UF and line['decisions'] == 'UF') or (applications_UF and line['choice_number'] == 'Final') or not applications_UF:
                        if (applications_UF and line['choice_number'] == 'Final') or not applications_UF:
                            if firstline:
                                firstline = False
                            else:
                                au += '\n'
                                ac += '\n'
                                ai += '\n'
                            au += line['institution_shortname']
                            ac += line['course_code']
                            ai += line['course_name'] + " (" + line['start_year'] + ") " + line.get('conditions','') + ' ' + line.get('decisions','')
                    tidykey = au + '","' + ac + '","' + ai
                elif key in progressionkeys:
                    tidykey = ""
                    firstline = True
                    for line in record.get('progressions',[]):
                        if firstline:
                            firstline = False
                        else:
                            tidykey += '\n'
                        if (key == 'starting_year'):
                            tidykey += line.get('starting_year',line.get('start_year',''))
                        else:
                            tidykey += line.get(key,"")
                elif key in ['school_qualifications','post_school_qualifications']:
                    unquote = False
                    qa = ''
                    ql = ''
                    firstline = True
                    for line in record[key]:
                        if firstline:
                            firstline = False
                        else:
                            qa += '\n'
                            ql += '\n'
                        qa += line['date'] + " grade " + line['grade'] + " in " + line['level'] + " " + line['subject'] + " (" + line['ftpt'] + ")"
                        ql += line['level']
                    tidykey = qa + '","' + ql
                else:
                    if isinstance(record[key],bool):
                        if record[key]:
                            tidykey = "yes"
                        else:
                            tidykey = "no"
                    elif isinstance(record[key],list):
                        tidykey = ",".join(record[key])
                    else:
                        tidykey = record[key]
                csvdata.write('"' + fixify(tidykey,unquote) + '"')
                if not unquote:
                    print fixify(tidykey,unquote)
            elif key in ['school_qualifications','post_school_qualifications']:
                csvdata.write('"",""')
            elif key == "applications":
                csvdata.write('"","",""')
            elif key not in ['applications_info','applications_course','school_qualifications_levels','post_school_qualifications_levels']:
                csvdata.write('""')
                
    # dump to the browser as a csv attachment
    csvdata.seek(0)
    return send_file(
        csvdata, 
        mimetype='text/csv',
        attachment_filename="swap_export_" + datetime.now().strftime("%d%m%Y%H%M") + ".csv",
        as_attachment=True
    )



