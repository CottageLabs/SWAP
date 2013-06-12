
import datetime

import json
from copy import deepcopy

from flask import Blueprint, request, flash, abort, make_response, render_template, redirect
from flask.ext.login import current_user

from portality.core import app
import portality.models as models


blueprint = Blueprint('reports', __name__)


# show the options for viewing / downloading generated reports, or perhaps offer building via facetview
@blueprint.route('/')
def index():
    return render_template('leaps/exports/index.html')




import cStringIO as StringIO
import reportlab, html5lib

# output the student details to a pdf template
def pdf():
    pass
    # only allow for staff
    # get the data for the student - or if no student print a blank pdf
    # get the student pdf template, and run it through the template renderer

    # should this be a blank PAE form requesting response, or a PAE form showing responses
    
    #template = get_template('student_pdf_template')
    #filename = "blank_form"
    #context = Context({"student":"obj")
    #html  = template.render(context)

    #result = StringIO.StringIO()
    #pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("ISO-8859-1", 'ignore')), result,)

    # email the PAE if appropriate
    
    # set the status to show the PAE has been sent, and to whom / why / when

    

# here are the old email methods to copy            
# write something to email a PAE form to an institute
'''
from django.core.mail import EmailMessage
def emailpae(paeform,unique_url="",to=['leaps@ed.ac.uk'],message=""):
    subject = "Pre-Application Enquiry from LEAPS"
    if not message:
        message = "LEAPS PAE form attached"
    fromwho = "leaps@ed.ac.uk"
    msg = EmailMessage(subject, message, fromwho, to, headers={'Reply-To': 'leaps@ed.ac.uk'})
    msg.attach('PAE_request.pdf',paeform,'application/pdf')
    msg.send()

# email the leaps admin when a PAE response is received
def emailadmin(paeid,to=['leaps@ed.ac.uk']):
    subject = "PAE response received"
    message = "A response has been received via the online response form.\n\n"
    message += "You can view the response at:\n\n"
    message += "https://leapssurvey.org/admin/leaps/pae/" + paeid
    message += "\n\nThanks!"
    fromwho = "leaps@ed.ac.uk"
    msg = EmailMessage(subject, message, fromwho, to, headers={'Reply-To': 'leaps@ed.ac.uk'})
    msg.send()
'''




# prep a pae for print / email
def ppae(request,admin_site):
    if not request.user.is_staff:
        return HttpResponseForbidden()

    ref = request.GET.get("pae","")
    if not ref:
        ref = request.POST.get("pae","")

    if request.method == "POST":
        if request.POST.get("email",None):
            emails = request.POST["emailaddress"].split(',')
            return pdfy(request,ref,"pae",emails,request.POST["content"])
        else:
            return pdfy(request,ref,"pae")
    else:
        paeobj = Pae.objects.get(pk=ref)
        
        message = "Request for Pre-application enquiry response\n\n"
        message += "Please find attached a PAE from LEAPS.\n\n"
        message += "To enable us to complete our work efficiently, we would appreciate if you could respond to this form "
        message += "via our online response collector. To do so, simply go to the following website address:\n\n"
        message += "https://leapssurvey.org/paes?i=" + str(ref)
        message += "\n\nIf you require input from multiple colleagues, please forward this email to those colleagues "
        message += "and request that they also use the online response collector."
        message += "\n\nThe relevant information you require to make your choices is included in the attached form.\n\n"
        message += "Alternatively, you can print the form and complete by hand, then return either by scanning and "
        message += "emailing back to us, or by post. Our email and postal addresses are also included on the form.\n\n"
        message += "This is an auto-generated email. If you have received this email in error, "
        message += "please contact us using the details below, or delete this email.\n\n"
        message += "Thank you very much for your help, and we look forward to hearing from you.\n\n"
        message += "The LEAPS team\n\n"
        message += "7 Buccleuch Place\nEdinburgh\nEH8 9LW\n\n"
        message += "leaps@ed.ac.uk\n0131 650 4676"

        render_vals = {
            "pae": ref,
            "paeobj":paeobj,
            "message":message
        }
        return render_to_response('ppae.html',render_vals,RequestContext(request, {}))
        

# pass the export start page for staff only
def exporter(request,admin_site):
    if not request.user.is_staff:
        return HttpResponseForbidden()
    if request.method == "POST":
        if request.POST["submit"] == "email":
            # email the report to someone
            email = request.POST["emailto"]
            return "Would email to " + email
        else:
            return serialise(request)
    elif not request.GET["ct"]:
        return render_to_response('export_front.html',)        
    else:
        fields = {}
        if ContentType.objects.get(pk=request.GET["ct"]).name in ["student","pae"]:
            sets = ['Student','ExtraAcademicAndCareer','Interest','WorkExperience','Qualification','Application','UnavailableSubject','Interview','School','Pae']
            ignores = ["student","id","created","last_altered","data_policy_agreement"]
        else:
            sets = ['Application']
            ignores = ["id"]
        if ContentType.objects.get(pk=request.GET["ct"]).name == "pae":
            # convert pae IDs to student IDs
            ids = []
            for pid in request.GET["ids"].split(','):
                sid = str(Pae.objects.get(pk=pid).student.id)
                if sid not in ids:
                    ids.append(sid)
            ids = ','.join(ids)
        else:
            ids = request.GET["ids"]
        for group in sets:
            fields[group] = []
            model = get_model('leaps',group)
            for field in model._meta.fields:
                if field.name not in ignores:
                    fields[group].append(field.name)
        render_vals = {
            'ct':request.GET["ct"],
            'ctn':ContentType.objects.get(pk=request.GET["ct"]).name,
            'ids':ids,
            'inst': request.GET.get('inst',''),
            'paeids': request.GET.get('ids',''),
            'getall': request.GET.get('getall',''),
            'archive': request.GET.get('archive',''),
            'fields':fields,
        }
        return render_to_response('export.html',render_vals,RequestContext(request, {}),)


# a function to serialize students to csv
def serialise(request):
    ids = [item for item in request.POST["ids"].split(",")]

    # check in case all were selected
    if 'archive' in request.POST:
        archid = request.POST['archive']
    else:
        archid = 1
    if 'getall' in request.POST:
        if request.POST['getall']:
            ids = []
            recs = Student.objects.filter(archive__id__exact=archid)
            for obj in recs:
                ids.append(obj.id)
        
    students = []
    for ref in ids:
        student = student_for_render(ref)
        cleanstudent = {}
        for model in student:
            if not student[model]:
                if model == 'ExtraAcademicAndCareer':
                    blank = {
                        "any_career_plans":"",
                        "late_decision_to_apply":"",
                        "had_recent_careers_interview":"",
                        "any_additional_qualifications":"",
                        "other_academic_issues":""
                    }
                elif model == 'Interview':
                    blank = {
                        "first_attending_university":"",
                        "mothers_occupation":"",
                        "fathers_occupation":"",
                        "number_of_siblings":"",
                        "place_in_siblings":"",
                        "household_composition":"",
                        "main_language_at_home":"",
                        "looked_after_child":"",
                        "low_income_family":"",
                        "young_carer":"",
                        "law_application":"",
                        "early_application":"",
                        "previous_interview":"",
                        "HN_only_candidate":"",
                        "PAE_action":"",
                        "additional_comments":"",
                        "created": "",
                        "last_altered":""
                    }
                else:
                    blank = {}
                student[model].append(blank)
#            if model == 'Pae':
#                cleanstudent[model] = student[model]
            if model+"---all" in request.POST:
                cleanstudent[model] = student[model]
            else:
                cleanrows = []
                for row in student[model]:
                    newrow = {}
                    for key,value in row.items():
                        if model+"---"+key in request.POST:
                            newrow[key] = value
                    if newrow:
                        cleanrows.append(newrow)
                cleanstudent[model] = cleanrows
#            if model not in cleanstudent.keys():
#                cleanstudent[model] = student[model]
        if cleanstudent:
            students.append(cleanstudent)
        #students.append(student)
    
    # if specific institute filter applied, restrict applications and paes to only that institute
    inst = request.POST.get('inst',False)
    if inst:
        for student in students:
            filteredapps = []
            filteredpaes = []
            for record in student['Application']:
                if record['institute'] == inst:
                    filteredapps.append(record)
            for record in student['Pae']:
                if record['institute'] == inst:
                    filteredpaes.append(record)
            student['Application'] = filteredapps
            student['Pae'] = filteredpaes
    
    response = HttpResponse(render_to_response('student_csv_template',{"students":students}), mimetype='text/csv',)
    response['Content-Disposition'] = "attachment; filename=report_%s.csv" % datetime.datetime.now().strftime("%d%m%Y")
    return response



