
from datetime import datetime

import cStringIO as StringIO
import string

import json, copy

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

    uniprogressionkeys = ['uni_starting_year','uni_course_name','uni_course_code','uni_institution_shortname','uni_decisions','uni_reg_1st_year','uni_1st_year_result','uni_reg_2nd_year','uni_2nd_year_result','uni_reg_3rd_year','uni_3rd_year_result','uni_reg_4th_year','uni_degree_classification_awarded']
    if 'uniprogression' in keys:
        keys.remove('uniprogression')
        for ky in uniprogressionkeys:
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

    if 'college_courses' in keys:
        i = keys.index('college_courses') + 1
        keys.insert(i,'completedunits')
        keys.insert(i,'profilegrades')
        keys.insert(i,'courseexit')
        keys.insert(i,'exitreason')
        keys.insert(i,'progress')
        keys.insert(i,'progresswhere')
        keys.remove('college_courses')

    college_progressionkeys = ['college_access_course','college_progress_where','college_campus','college_course_name','college_reg_1st_year','college_1st_year_result','college_reg_2nd_year','college_2nd_year_result','college_progression_to_university']
    if 'college_progression' in keys:
        keys.remove('college_progression')
        for ky in college_progressionkeys:
            keys.append(ky)

    if 'withdrawn' in keys:
        i = keys.index('withdrawn') + 1
        keys.insert(i,'exitreason')
        keys.insert(i,'courseexit')
        
    if 'date_of_birth' in keys:
        i = keys.index('date_of_birth') + 1
        keys.insert(i,'ageonentry')

    if 'applications' in keys:
        i = keys.index('applications') + 1
        keys.insert(i,'decisions')
        keys.insert(i,'conditions')
        keys.insert(i,'start_year')
        keys.insert(i,'course_name')
        keys.insert(i,'course_code')

    if 'school_qualifications' in keys:
        i = keys.index('school_qualifications') + 1
        keys.insert(i,'school_qualifications_levels')

    if 'post_school_qualifications' in keys:
        i = keys.index('post_school_qualifications') + 1
        keys.insert(i,'post_school_qualifications_levels')

    # convert ucas applications recordlist to output a student on every line
    hasappns = False
    longrecordlist = []
    for rec in recordlist:
        if 'applications' in keys and rec.get('applications',False):
            hasappns = True
            rapps = copy.deepcopy(rec['applications'])
            for ra in rapps:
                nr = copy.deepcopy(rec)
                nr['applications'] = [ra]
                longrecordlist.append(nr)
        else:
            longrecordlist.append(rec)

    # make a csv string of the records
    csvdata = StringIO.StringIO()
    firstrecord = True
    for record in longrecordlist:
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
            elif key not in ['course_code','course_name','start_year','conditions','decisions','school_qualifications_levels','post_school_qualifications_levels']:
                csvdata.write(',')
            if key in record.keys() or key == 'address' or key in uniprogressionkeys or key in college_progressionkeys:
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
                    #ai = ''
                    an = ''
                    asy = ''
                    aco = ''
                    ade = ''
                    firstline = True
                    for line in record[key]:
                        #if ( applications_UF and 'UF' in line['decisions'] ) or (applications_UF and line['decisions'] == 'UF') or (applications_UF and line['choice_number'] == 'Final') or not applications_UF:
                        if (applications_UF and line['choice_number'] == 'Final') or not applications_UF:
                            if firstline:
                                firstline = False
                            else:
                                au += '\n'
                                ac += '\n'
                                #ai += '\n'
                                an += '\n'
                                asy += '\n'
                                aco += '\n'
                                ade += '\n'
                            au += line['institution_shortname']
                            ac += line['course_code']
                            #ai += line['course_name'] + " (" + line['start_year'] + ") " + line.get('conditions','') + ' ' + line.get('decisions','')
                            an += line['course_name']
                            asy += line['start_year']
                            aco += line['conditions']
                            ade += line['decisions']
                    #tidykey = au + '","' + ac + '","' + ai
                    tidykey = au + '","' + ac + '","' + an + '","' + asy + '","' + aco + '","' + ade
                elif key in uniprogressionkeys:
                    ky = key.replace('uni_','')
                    tidykey = ""
                    firstline = True
                    for line in record.get('progressions',[]):
                        if firstline:
                            firstline = False
                        else:
                            tidykey += '\n'
                        if (ky == 'starting_year'):
                            tidykey += line.get('starting_year',line.get('start_year',''))
                        else:
                            tidykey += line.get(ky,"")
                elif key in college_progressionkeys:
                    ky = key.replace('college_','')
                    tidykey = ""
                    firstline = True
                    for line in record.get('college_progressions',[]):
                        if firstline:
                            firstline = False
                        else:
                            tidykey += '\n'
                        tidykey += line.get(ky,"")
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
            elif key not in ['course_code','course_name','start_year','conditions','decisions','school_qualifications_levels','post_school_qualifications_levels'] and (not hasappns or key not in ['course_name','start_year','conditions','decisions']):
                csvdata.write('""')
                
    # dump to the browser as a csv attachment
    csvdata.seek(0)
    return send_file(
        csvdata, 
        mimetype='text/csv',
        attachment_filename="swap_export_" + datetime.now().strftime("%d%m%Y%H%M") + ".csv",
        as_attachment=True
    )



