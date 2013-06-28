
from datetime import datetime
import cStringIO as StringIO

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
    query = json.loads(request.values.get('query','{"query":{"match_all":{}}}'))
    if 'size' in request.values: query['size'] = request.values['size']
    selected = json.loads(request.values.get('selected','[]'))

    if request.method == 'GET':
        return render_template('swap/exports/index.html', query=json.dumps(query), selected=json.dumps(selected))

    elif request.method == 'POST':
        keys = request.form.keys()
        s = models.Student.query(q=query)
        students = []
        for i in s.get('hits',{}).get('hits',[]): 
            if (selected and i['_source']['id'] in selected) or not selected:
                students.append(i['_source'])
        
        keys.remove('query')
        keys.remove('submit')
        keys.remove('selected')
        
        return download_csv(students,keys)


def download_csv(recordlist,keys):
    # make a csv string of the records
    csvdata = StringIO.StringIO()
    firstrecord = True
    for record in recordlist:
        # make sure this record has all the keys we would expect
        for key in keys:
            if key not in record.keys():
                record[key] = ""
        # for the first one, put the keys on the first line, otherwise just newline
        if firstrecord:
            fk = True
            for key in sorted(record.keys()):
                if key in keys: # ignore keys that have not been selected by the user
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
        for key in sorted(record.keys()):
            if key in keys:
                if firstkey:
                    firstkey = False
                else:
                    csvdata.write(',')
                if key in ['applications','interests','qualifications','experience']:
                    tidykey = ""
                    firstline = True
                    for line in record[key]:
                        if firstline:
                            firstline = False
                        else:
                            tidykey += '\n'
                        if key == 'applications':
                            tidykey += line['level'] + " " + line['subject'] + " at " + line['institution']
                        elif key == 'interests':
                            tidykey += line['title'] + " - " + line['brief_description']
                        elif key =='qualifications':
                            tidykey += line['year'] + " grade " + line['grade'] + " in " + line['level'] + " " + line['subject']
                        elif key == 'experience':
                            tidykey += line['date_from'] + " to " + line['date_to'] + " " + line['title'] + " - " + line['brief_description']
                elif key in ['address']:
                    pass # TODO: need specific handling to turn individual address tick to all address fields (but not post_code)
                else:
                    if isinstance(record[key],bool):
                        if record[key]:
                            tidykey = "true"
                        else:
                            tidykey = "false"
                    else:
                        tidykey = record[key].replace('"',"'")
                csvdata.write('"' + tidykey + '"')

    # dump to the browser as a csv attachment
    csvdata.seek(0)
    return send_file(
        csvdata, 
        mimetype='text/csv',
         attachment_filename="swap_export_" + datetime.now().strftime("%d%m%Y%H%M") + ".csv",
        as_attachment=True
    )
            

