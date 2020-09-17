
from datetime import datetime

from portality.core import app

from portality.dao import DomainObject as DomainObject

import requests, json

'''
Define models in here. They should all inherit from the DomainObject, or an object that does.
Look in the dao.py to learn more about the default methods available to the Domain Object.
'''


class Student(DomainObject):
    __type__ = 'student'

    def save(self):
        if 'id' in self.data:
            id_ = self.data['id'].strip()
        else:
            id_ = self.makeid()
            self.data['id'] = id_
        
        self.data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H%M")

        if 'archive' not in self.data:
            self.data['archive'] = 'current'

        if 'created_date' not in self.data:
            self.data['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
        
        if 'status' not in self.data or self.data['status'] == "":
            # TODO: ensure this sets first status to the correct one
            self.data['status'] = 'new'

        if 'simd_decile' not in self.data or self.data['simd_decile'] == "":
            s = Simd.pull_by_post_code(self.data['post_code'])
            if s is not None:
                self.data['simd_decile'] = s.data.get('simd_decile','SIMD decile missing')
                self.data['simd_quintile'] = s.data.get('simd_quintile','SIMD quintile missing')
            else:
                self.data['simd_decile'] = 'unknown'
                self.data['simd_quintile'] = 'unknown'

        if 'college' in self.data:
            c = Course().pull_by_ccc(self.data['college'],self.data['campus'],self.data.get('course',False))
            if c is not None:
                self.data['locale'] = c.data.get('locale',"")
                self.data['region'] = c.data.get('region',"")
                self.data['classification'] = c.data.get('classification',"")
                self.data['previous_name'] = c.data.get('previous_name',"")

        if 'date_of_birth' in self.data:
            if '-' in self.data['date_of_birth']: self.data['date_of_birth'].replace('-','/')
            parts = self.data['date_of_birth'].split('/')
            if len(str(parts[2])) == 2:
                if parts[2] > 50:
                    year = str("19" + str(parts[2]))
                else:
                    year = str("20" + str(parts[2]))
                self.data['date_of_birth'] = str(parts[0]) + '/' + str(parts[1]) + '/' + str(year)
            if not self.data.get('ageonentry',False):
                # calculate age on 1st August of current year
                year = datetime.now().year
                # if before 1st August of current year, subtract 1
                if datetime.now().month < 8: year -= 1
                ayear = datetime(year, 8, 1)
                difference = ayear - datetime.strptime(self.data['date_of_birth'], '%d/%m/%Y')
                age = (difference.days + difference.seconds/86400.0)/365.2425
                self.data['ageonentry'] = int(age)

        if len(self.data.get('other_english',"")) > 1 or len(self.data.get('other_maths',"")) > 1:
            self.data['other_qualifications'] = True
        else:
            self.data['other_qualifications'] = False

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))


    def save_from_form(self, request):
        applications = []
        progressions = []
        schoolquals = []
        postschoolquals = []
        
        if 'has_highers' not in self.data: self.data['has_highers'] = False
        highers = ['Higher','Higher Grade','Advanced Higher','Baccalaureate','Bachillerato','High School Diploma','High School leavers certificate','Matura']

        for k,v in enumerate(request.form.getlist('school_qualification_subject')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    schoolqual = {
                        "subject": v,
                        "level": request.form.getlist('school_qualification_level')[k],
                        "grade": request.form.getlist('school_qualification_grade')[k],
                        "date": request.form.getlist('school_qualification_date')[k],
                        "ftpt": request.form.getlist('school_qualification_ftpt')[k]
                    }
                    if schoolqual['level'] in highers: self.data['has_highers'] = True
                    schoolquals.append(schoolqual)
                except:
                    pass

        for k,v in enumerate(request.form.getlist('post_school_qualification_subject')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    postschoolqual = {
                        "subject": v,
                        "level": request.form.getlist('post_school_qualification_level')[k],
                        "grade": request.form.getlist('post_school_qualification_grade')[k],
                        "date": request.form.getlist('post_school_qualification_date')[k],
                        "ftpt": request.form.getlist('post_school_qualification_ftpt')[k]
                    }
                    if postschoolqual['level'] in highers: self.data['has_highers'] = True
                    postschoolquals.append(postschoolqual)
                except:
                    pass

        for k,v in enumerate(request.form.getlist('application_institution_code')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    appn = {
                        "choice_number": request.form.getlist('application_choice_number')[k],
                        "institution_code": v,
                        "institution_shortname": request.form.getlist('application_institution_shortname')[k],
                        "course_code": request.form.getlist('application_course_code')[k],
                        "conditions": request.form.getlist('application_conditions')[k],
                        "course_name": request.form.getlist('application_course_name')[k],
                        "start_year": request.form.getlist('application_start_year')[k]
                    }
                    applications.append(appn)
                except:
                    pass

        for k,v in enumerate(request.form.getlist('progression_institution_shortname')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    prog = {
                        "institution_shortname": v
                    }
                    progressions.append(prog)
                except:
                    pass

        if len(applications) > 0: self.data['applications'] = applications
        if len(progressions) > 0: self.data['progressions'] = progressions
        if len(schoolquals) > 0: self.data['school_qualifications'] = schoolquals
        if len(postschoolquals) > 0: self.data['post_school_qualifications'] = postschoolquals

        # clean tickboxes
        tickboxes = [
            'registered',
            'attended',
            'withdrawn',
            'parents_with_hnc',
            'siblings_with_hnc',
            'parents_with_hnd',
            'siblings_with_hnd',
            'parents_with_degree',
            'siblings_with_degree',
            'registered_disabled'
        ]
        old_qual_tickboxes = [
            'other_qualifications',
            'previous_level6_qualifications'          
        ]
        new_qual_tickboxes = [
            'no_school_quals',
            'no_post_school_quals',
            'maths_level6_taken',
            'english_level6_taken'
        ]
        if 'other_qualifications' in request.form.keys() or 'previous_level6_qualifications' in request.form.keys():
            tickboxes = tickboxes + old_qual_tickboxes
        else:
            tickboxes = tickboxes + new_qual_tickboxes
        for k in tickboxes:
            self.data[k] = False

        for key in request.form.keys():
            if request.form[key] == "on":
                self.data[key] = True
            elif request.form[key] == "off":
                self.data[key] = False
            elif key in ['nationality','first_name','last_name'] and len(request.form[key]) > 1:
                self.data[key] = request.form[key].strip()[0].upper() + request.form[key].strip()[1:]
            elif not key.startswith('application_') and not key.startswith('progression_') and not key.startswith('school_qualification_') and not key.startswith('post_school_qualification_') and key not in ['submit']:
                self.data[key] = request.form[key]
        
        if "college" not in self.data:
            self.data["college"] = ""
        if "course" not in self.data:
            self.data["course"] = ""
        if "campus" not in self.data:
            self.data["campus"] = ""

        old_qual_keys = [
            'o_standard_gcse',
            'intermediate2',
            'highers_alevels',
            'other_school_qualifications',
            'qualifications_after_school',
            'other_maths',
            'other_english',
            'other_qualifications',
            'previous_level6_qualifications'
        ]
        if 'school_qualifications' not in self.data and 'post_school_qualifications' not in self.data:
            old = False
            for k in old_qual_keys:
                if k in self.data:
                    old = True
            if not old:
                self.data['school_qualfications'] = []
                self.data['post_school_qualifications'] = []
                
        self.save()


class Progression(DomainObject):
    __type__ = "progression"

    @classmethod
    def delete_east(cls):
        qry = {
            'query': {
                'term': {
                    'locale.exact': 'East'
                }
            },
            'fields': [],
            'size': 100000
        }
        res = cls.query(q=qry)
        for rec in res.get('hits',{}).get('hits',[]):
            requests.delete(cls.target() + rec['_id'])

    @classmethod
    def delete_west(cls):
        qry = {
            'query': {
                'term': {
                    'locale.exact': 'West'
                }
            },
            'fields': [],
            'size': 100000
        }
        res = cls.query(q=qry)
        for rec in res.get('hits',{}).get('hits',[]):
            requests.delete(cls.target() + rec['_id'])


class Uninote(DomainObject):
    __type__ = "uninote"

    @classmethod
    def pull_by_name(cls, name):
        r = cls.query(q={"query":{"term":{"name"+app.config['FACET_FIELD']:name}}})
        try:
            return cls.pull( r['hits']['hits'][0]['_source']['id'] )
        except:
            return None

    def save_from_form(self, request):
    
        for key in request.form.keys():
            if key not in ['submit']:
                val = request.form[key]
                if val == "on":
                    self.data[key] = True
                elif val == "off":
                    self.data[key] = False
                else:
                    self.data[key] = val
        
        self.save()

    
class Course(DomainObject):
    __type__ = 'course'

    @classmethod
    def pull_by_ccc(cls, college, campus=False, course=False):
        qry = {
            "query": {
                "bool": {
                    "must":[
                        {
                            "term": {
                                "college" + app.config['FACET_FIELD'] : college
                            }
                        }
                    ]
                }
            }
        }
        if campus:
            qry['query']['bool']['must'].append({"term":{"campus"+app.config['FACET_FIELD']:campus}})
        if course:
            qry['query']['bool']['must'].append({"term":{"course"+app.config['FACET_FIELD']:course}})
        found = cls.query(q=qry)
        if found.get('hits',{}).get('total',0) != 0:
            return cls.pull(found['hits']['hits'][0]['_source']['id'])
        else:
            return None
            

    def delete(self):
        # delete contact accounts
        for c in self.data.get('contacts',[]):
            if c['email'] != "":
                exists = Account.pull(c['email'])
                if exists is not None:
                    exists.delete()
        r = requests.delete(self.target() + self.id)


    def save(self):
        if 'id' in self.data:
            id_ = self.data['id'].strip()
        else:
            id_ = self.makeid()
            self.data['id'] = id_
        
        self.data['last_updated'] = datetime.now().strftime("%Y-%m-%d %H%M")

        if 'created_date' not in self.data:
            self.data['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
        
        if 'previous_name' not in self.data:
            self.data['previous_name'] = []
        if 'region' not in self.data:
            self.data['region'] = ""
        if 'campus' not in self.data:
            self.data['campus'] = ""
        if 'classification' not in self.data:
            self.data['classification'] = ""

        if not isinstance(self.data.get('previous_name',""),list):
            self.data['previous_name'] = self.data.get('previous_name',"").split(",")

        old = Course.pull(self.id)
        if old is not None:
            if old.data['college'] != self.data['college'] and old.data['college'] not in self.data['previous_name']:
                self.data['previous_name'].append(old.data['college'])
            # remove any old accounts
            for oc in old.data.get('contacts',[]):
                if oc.get('email',"") not in [o.get('email',False) for o in self.data.get('contacts',[])]:
                    oldaccount = Account.pull(oc.get('email',""))
                    if oldaccount is not None: oldaccount.delete()

        for c in self.data.get('contacts',[]):
            # create any new accounts
            if c.get('email',"") != "" and ( old is None or c.get('email',"") not in [o.get('email',False) for o in old.data.get('contacts',[])] ):
                account = Account.pull(c['email'])
                if account is None:
                    c['email'] = c['email'].lower()
                    account = Account(
                        id=c['email'], 
                        email=c['email']
                    )
                    account.data[self.__type__] = self.id # TODO: how will user be related to students via their courses?
                    if len(c.get("password","")) > 1:
                        pw = c['password']
                        c['password'] = ""
                    else:
                        pw = "password"
                    account.set_password(pw)
                    account.save()
            # change any passwords
            elif c.get('email',"") != "" and c.get('password',"") != "":
                account = Account.pull(c['email'])
                account.set_password(c['password'])
                account.save()
                c['password'] = ""

        for item in self.data['previous_name']:
            if len(item) == 0: self.data['previous_name'].remove(item)

        if 'locale' in self.data and len(self.data['locale']) > 1:
            self.data['locale'] = self.data['locale'][0].upper() + self.data['locale'][1:]
            if self.data['locale'].lower() not in ['east','west']:
                self.data['locale'] = 'East'
        else:
            self.data['locale'] = 'East'

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))




    def save_from_form(self, request):
        rec = {
            "contacts": []
        }
        
        for k,v in enumerate(request.form.getlist('contact_email')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    rec["contacts"].append({
                        "name": request.form.getlist('contact_name')[k],
                        "email": v,
                        "password": request.form.getlist('contact_password')[k]
                    })
                except:
                    pass

        for key in request.form.keys():
            if not key.startswith("contact_") and key not in ['submit']:
                val = request.form[key]
                if val == "on":
                    rec[key] = True
                elif val == "off":
                    rec[key] = False
                else:
                    rec[key] = val

        if len(rec['contacts']) == 0: del rec['contacts']
        for k, v in rec.items():
            self.data[k] = v
            
        for kk, vv in self.data.items():
            if vv == True and kk not in request.form.keys():
                del self.data[kk]
        
        self.save()




class Schoolsubject(DomainObject):
    __type__ = 'schoolsubject'
    
    def save_from_form(self, request):
        for key in request.form.keys():
            if key not in ['submit']:
                val = request.form[key]
                self.data[key] = val        
        self.save()

class Schoollevel(DomainObject):
    __type__ = 'schoollevel'

    def save_from_form(self, request):
        for key in request.form.keys():
            if key not in ['submit']:
                val = request.form[key]
                self.data[key] = val        
        self.save()

class Postschoollevel(DomainObject):
    __type__ = 'postschoollevel'

    def save_from_form(self, request):
        for key in request.form.keys():
            if key not in ['submit']:
                val = request.form[key]
                self.data[key] = val        
        self.save()




class Simd(DomainObject):
    __type__ = 'simd'

    @classmethod
    def prep(cls, rec):
        if 'id' not in rec:
            if 'post_code' in rec:
                rec['id'] = rec['post_code'].lower().replace(" ","")
            else:
                rec['id'] = cls.makeid()
        
        rec['last_updated'] = datetime.now().strftime("%Y-%m-%d %H%M")

        if 'created_date' not in rec:
            rec['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
            
        if 'author' not in rec:
            try:
                rec['author'] = current_user.id
            except:
                rec['author'] = "anonymous"
                
        return rec

    @classmethod
    def pull_by_post_code(cls, post_code):
        return cls.pull(post_code.lower().replace(" ",""))


class Archive(DomainObject):
    __type__ = 'archive'

    def __len__(self):
        res = Student.query(terms={"archive"+app.config['FACET_FIELD']:self.data["name"]})
        return res['hits']['total']
    
    def delete(self):
        for kid in self.children(justids=True):
            k = Student.pull(kid)
            k.delete()
        r = requests.delete(self.target() + self.id)
    
    def children(self,justids=False):
        kids = []
        res = Student.query(terms={"archive"+app.config['FACET_FIELD']:self.data["name"]}, size=100000)
        if res['hits']['total'] != 0:
            if justids:
                kids = [i['_source']['id'] for i in res['hits']['hits']]
            else:
                kids = [i['_source'] for i in res['hits']['hits']]
        return kids

    @classmethod
    def pull_by_name(cls, name):
        r = cls.query(q={"query":{"term":{"name"+app.config['FACET_FIELD']:name}}})
        try:
            return cls.pull( r['hits']['hits'][0]['_source']['id'] )
        except:
            return None



# The account object, which requires the further additional imports
import portality.auth as auth
from werkzeug import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin

class Account(DomainObject, UserMixin):
    __type__ = 'account'

    def set_password(self, password):
        self.data['password'] = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.data['password'], password)

    @property
    def is_super(self):
        return auth.user.is_super(self)

    @property
    def do_admin(self):
        return auth.user.do_admin(self)

    @property
    def view_admin(self):
        return auth.user.view_admin(self)

    @property
    def is_course_manager(self):
        return auth.user.is_course_manager(self)
            
    @property
    def agreed_policy(self):
        if not isinstance(self.is_course_manager,bool):
            return self.data.get('agreed_policy',False)
        else:
            return True

    
# a special object that allows a search onto all index types - FAILS TO CREATE INSTANCES
class Everything(DomainObject):
    __type__ = 'everything'

    @classmethod
    def target(cls):
        t = 'http://' + str(app.config['ELASTIC_SEARCH_HOST']).replace('http://','').rstrip('/') + '/'
        t += app.config['ELASTIC_SEARCH_DB'] + '/'
        return t


