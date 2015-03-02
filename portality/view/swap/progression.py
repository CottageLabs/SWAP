
from flask import Blueprint, request, render_template, abort
from flask.ext.login import current_user

from portality.core import app
from portality.view.swap.forms import dropdowns

import portality.models as models


blueprint = Blueprint('progression', __name__)


# a forms overview page at the top level, can list forms or say whatever needs said about forms, or catch closed forms
@blueprint.route('/')
@blueprint.route('/<locale>')
@blueprint.route('/<locale>')
def progression(locale=''):
    #if locale == '': locale = 'East'
    qry = {
        'query':{
            'bool':{
                'must':[
                    {
                        'match_all': {}
                    }
                ]
            }
        },
        'size': 0,
        'facets':{}
    }

    if locale.lower() == 'east':
        locale = 'East'
        qry['query']['bool']['must'].append({
            'term':{
                'locale'+app.config['FACET_FIELD']: locale
            }
        })
    elif locale.lower() == 'west':
        locale = 'West'
        qry['query']['bool']['must'].append({
            'term':{
                'locale'+app.config['FACET_FIELD']: locale
            }
        })

    keys = ['access_course_college','access_course_name','degree_course_name','degree_institution_name']
    res = {}
    for key in keys:
        qry['facets'][key] = {"terms":{"field":key+app.config['FACET_FIELD'],"order":'term', "size":100000}}
        r = models.Progression().query(q=qry)
        res[key] = [i.get('term','') for i in r.get('facets',{}).get(key,{}).get("terms",[])]
    
    return render_template(
        'swap/progression.html',
        locale=locale,
        selections={
            "colleges": res['access_course_college'],
            "accesscourses": res['access_course_name'],
            "degrees": res['degree_course_name'],
            "institutions": res['degree_institution_name']
        }
    )
        

@blueprint.route('/notes/<uni>')
def notes(uni):
    uninote = models.Uninote.pull_by_name(uni)
    if uninote is None:
        abort(404)
    else:
        swap_note = 'This information is intended as a guide to SWAP applicants and their tutors for help with potential progression routes to University. Every effort has been made by SWAP East to ensure that the information is accurate at time of publication. Universities reserve the right to alter conditions of entry without notice and SWAP East will not be held liable for information that is subject to change. Whilst SWAP East will make every effort to advise students of such changes it is not responsible for any consequence which may result.'
        
        notes = uninote.data['notes']
        if len(notes) == 0:
            notes = "<p>There are no additional notes from " + uni + "</p>"
        else:
            notes = notes.lstrip('\n').rstrip('\n').replace('\n\n\n','\n\n').replace('\n\n','</p><p>').replace('\n','<br>')
            notes = '<p><b>Notes provided by ' + uni + '</b><br>' + notes + '</p>'

        notes += '</div><div class="well"><p><b>SWAP additional note</b><br>' + swap_note + '</p>'
            
        contacts = '<p><b>' + uni + ' contacts</b></p><p>' + uninote.data['contacts'].lstrip('\n').rstrip('\n').replace('\n\n\n','\n\n').replace('\n\n','</p><p>').replace('\n','<br>') + '</p>'

        return render_template('swap/notes.html', uninote=uninote, notes=notes, contacts=contacts)




