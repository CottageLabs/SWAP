
from flask.ext.wtf import Form, TextField, TextAreaField, SelectField, PasswordField, BooleanField, DateField, FormField, validators, ValidationError

# methods to get choices for different fields
def schools():
    return [('',''), ('school1','school1'),('school2','school2')]

def years():
    return [('',''), ('year1','year1'),('year2','year2')]

def subjects():
    return [('',''), ('subject1','subject1'),('subject2','subject2')]

def levels():
    return [('',''), ('level1','level1'),('level2','level2')]

def grades():
    return [('',''), ('grade1','grade1'),('grade2','grade2')]

def institutes():
    return [('',''), ('grade1','grade1'),('grade2','grade2')]

def advancedlevels():
    return [('',''), ('grade1','grade1'),('grade2','grade2')]



class Student(Form):
    title = "Your details"
    explanation = "<strong>Page 1 of 6</strong> - please provide your personal details below, to create your record."

    def agrees(form, field):
        if form.data_policy_agreement.data != "yes":
            raise ValidationError('You must agree to our data policy in order to continue')
            
    first_name = TextField('First name', [validators.Required()])
    last_name = TextField('Last name', [validators.Required()])
    date_of_birth = DateField('Date of birth', [validators.Required()],format='%d/%m/%Y')
    ucas_number = TextField('UCAS number')
    gender = SelectField('Gender', [validators.Required()], choices=[('',''), ('male','Male'),('female','Female')])
    school = SelectField('School', [validators.Required()], choices=schools())
    school_house = TextField('School House')
    year_group = SelectField('Year group', [validators.Required()], choices=years())
    email_address = TextField('Email address', [validators.Required(), validators.Email(message='Must be a valid email address')])
    home_phone = TextField('Home phone')
    mobile_phone = TextField('Mobile phone')
    address = TextField('Address', [validators.Required()])
    address_line_2 = TextField('...')
    city = TextField('City', [validators.Required()])
    region = TextField('Region')
    post_code = TextField('Post code', [validators.Required()])
    data_policy_agreement = SelectField('I agree to the LEAPS data policy', [agrees], choices=[('',''), ('yes','Yes'),('no','No')], description='<a target="_blank" href="/policy">View our data policy</a>')

    previous = None
    next = "Qualification"
    

class Quallist(Form):
    subject = SelectField('Subject', [validators.Required()], choices=subjects())
    year = SelectField('Year', [validators.Required()], choices=years())
    level = SelectField('Level', [validators.Required()], choices=levels())
    grade = SelectField('Grade', [validators.Required()], choices=grades())
class Qualification(Form):
    title = "Qualifications and Currently Sitting"
        
    explanation = "<strong>Page 2 of 6</strong> - please provide details of your <strong>exam results to date AND subjects you are currently sitting</strong>. <br /><br />If you do not yet know your grade, select Unknown in the Grade field. If you have any qualifications that do not meet the criteria below, you will have the option to describe them on the following pages. Use one row per qualification."

    headers = ["Subject","School year taken","Level of qualification","Grade"]
        
    formlist = FormField(Quallist)

    previous = "Student"
    next = "Application"
    

class Applist(Form):
    institute = SelectField('Institute', [validators.Required()], choices=institutes())
    subject = SelectField('Subject', [validators.Required()], choices=subjects())
    level = SelectField('Level', [validators.Required()], choices=advancedlevels())
class Application(Form):
    title= "Potential Applications"
        
    explanation = "<strong>Page 3 of 6</strong> - please list any applications for further or higher education that you are thinking of making. Use one row per application, up to the maximum of 6. If you have not made any decisions yet, please feel free to leave this section blank."

    headers = ["College / University","Subject","Level of study"]

    formlist = FormField(Applist)

    previous = "Qualification"
    next = "Interest"
    

class Intlist(Form):
    name = TextField('Name', [validators.Required()])
    brief_description = TextAreaField('Brief description', [validators.Required()])
class Interest(Form):
    title = "Interests and achievements"
        
    explanation = "<strong>Page 4 of 6</strong> - please give brief descriptions of your extra-curricular interests and achievements e.g. sport, music, drama, Duke of Edinburgh, prefect etc. Use one box per interest, up to the maximum of 6."

    headers = ["Title","Brief description"]

    formlist = FormField(Intlist)

    previous = "Application"
    next = "Experience"


class Explist(Form):
    date_from = TextField('Date from', [validators.Required()])
    date_to = TextField('Date to', [validators.Required()])
    where = TextField('Where', [validators.Required()])
    brief_description = TextAreaField('Brief description', [validators.Required()])
class Experience(Form):
    title = "Work and other experience"
        
    explanation = "<strong>Page 5 of 6</strong> - please give brief descriptions of any work or voluntary experience you have had e.g. paid employment, school committees, Pathways to Professions events. Use one row per experience, up to the maximum of 6."

    headers = ["Date from","Date to","Title","Brief description"]

    formlist = FormField(Explist)

    previous = "Interest"
    next = "Extra"
    

class Extra(Form):
    title = "Additional academic and career information"
        
    explanation = "<strong>Page 6 of 6</strong> - please provide information about any other factors that affected your academic achievements, and provide some details on your career goals and any plans you have made towards them."

    late_decision_to_apply = BooleanField()
    had_recent_careers_interview = BooleanField()
    any_additional_qualifications = TextAreaField()
    other_academic_issues = TextAreaField()
    any_career_plans = TextAreaField()
    
    previous = "Experience"
    next = None



'''

# if an extra input row is requested, provide it
#def row_add(request,FormSet):
#    cp = request.POST.copy()
#    cp['form-TOTAL_FORMS'] = int(cp['form-TOTAL_FORMS']) + 1
#    return FormSet(cp, request.FILES)

'''



