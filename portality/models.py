
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

        if 'college' in self.data and 'locale' not in self.data:
            c = Course().pull_by_ccc(self.data['college'],self.data['campus'],self.data.get('course',False))
            if c is not None:
                self.data['locale'] = c.data.get('locale',"")
                self.data['region'] = c.data.get('region',"")
                self.data['classification'] = c.data.get('classification',"")
                self.data['previous_name'] = c.data.get('previous_name',"")

        if len(self.data.get('other_english',"")) > 1 or len(self.data.get('other_maths',"")) > 1:
            self.data['other_qualifications'] = True
        else:
            self.data['other_qualifications'] = False

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))


    def save_from_form(self, request):
        applications = []
        progressions = []
        
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

        for k,v in enumerate(request.form.getlist('progression_year')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    prog = {
                        "year": v,
                        "status": request.form.getlist('progression_status')[k]
                    }
                    progressions.append(prog)
                except:
                    pass

        if len(applications) > 0: self.data['applications'] = applications
        if len(progressions) > 0: self.data['applications'] = applications

        for key in request.form.keys():
            if key == 'nationality' and len(request.form[key]) > 1:
                self.data[key] = request.form[key][0].upper() + request.form[key][1:]
            elif not key.startswith('application_') and not key.startswith('progression_') and key not in ['submit']:
                self.data[key] = request.form[key]

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
        # delete contact account
        if self.data.get('contact_email',"") != "":
            exists = Account.pull(self.data['contact_email'])
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

        old = Course.pull(self.id)
        if old is not None:
            if old.data['college'] != self.data['college']:
                self.data['previous_name'].append(old.data['college'])
            # remove any old accounts
            if self.data.get('contact_email',"") != old.data.get('contact_email',False):
                oldaccount = Account.pull(old.data.get('contact_email',""))
                if oldaccount is not None: oldaccount.delete()

        # create any new accounts
        if self.data.get('contact_email',"") != "" and ( old is None or self.data.get('contact_email',"") != old.data.get('contact_email',False) ):
            account = Account.pull(self.data['contact_email'])
            if account is None:
                account = Account(
                    id=self.data['contact_email'], 
                    email=self.data['contact_email']
                )
                account.data[self.__type__] = self.id
                if len(self.data.get("contact_password","")) > 1:
                    pw = self.data['contact_password']
                    del self.data['contact_password']
                else:
                    pw = "password"
                account.set_password(pw)
                account.save()
        # change any passwords
        elif self.data.get('contact_email',"") != "" and self.data.get('contact_password',"") != "":
            account = Account.pull(self.data['contact_email'])
            account.set_password(self.data['contact_password'])
            account.save()
            del self.data['contact_password']

        if not isinstance(self.data.get('previous_name',""),list):
            self.data['previous_name'] = self.data.get('previous_name',"").split(",")
        if 'previous_name' not in self.data: self.data['previous_name'] = []

        if 'locale' in self.data and len(self.data['locale']) > 1:
            self.data['locale'] = self.data['locale'][0].upper() + self.data['locale'][1:]
            if self.data['locale'].lower() not in ['east','west']:
                self.data['locale'] = 'East'
        else:
            self.data['locale'] = 'East'

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))

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
        t = 'http://' + str(app.config['ELASTIC_SEARCH_HOST']).lstrip('http://').rstrip('/') + '/'
        t += app.config['ELASTIC_SEARCH_DB'] + '/'
        return t


