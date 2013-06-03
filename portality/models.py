
from datetime import datetime

from portality.core import app

from portality.dao import DomainObject as DomainObject

import requests, json

'''
Define models in here. They should all inherit from the DomainObject.
Look in the dao.py to learn more about the default methods available to the Domain Object.
When using portality in your own flask app, perhaps better to make your own models file somewhere and copy these examples
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

        if 'leaps_category' not in self.data or self.data['leaps_category'] == "":
            s = School.query(q={'query':{'term':{'name.exact':self.data['school']}}})
            if s.get('hits',{}).get('total',0) == 0:
                self.data['leaps_category'] = "unknown"
                self.data['shep_school'] = "unknown"
                self.data['local_authority'] = "unknown"
            else:
                self.data['leaps_category'] = s.get('hits',{}).get('hits',[])[0]['_source'].get('leaps_category','unknown')
                self.data['shep_school'] = s.get('hits',{}).get('hits',[])[0]['_source'].get('shep_school','unknown')
                self.data['local_authority'] = s.get('hits',{}).get('hits',[])[0]['_source'].get('local_authority','unknown')

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))

    def save_from_form(self, request):
        rec = {
            "qualifications": [],
            "interests": [],
            "applications": [],
            "experience": []
        }
        
        for k,v in enumerate(request.form.getlist('qualification_subject')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    rec["qualifications"].append({
                        "subject": v,
                        "year": request.form.getlist('qualification_year')[k],
                        "level": request.form.getlist('qualification_level')[k],
                        "grade": request.form.getlist('qualification_grade')[k]
                    })
                except:
                    pass
        for k,v in enumerate(request.form.getlist('interest_title')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    rec["interests"].append({
                        "title": v,
                        "brief_description": request.form.getlist('interest_brief_description')[k]
                    })
                except:
                    pass
        for k,v in enumerate(request.form.getlist('application_subject')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    rec["applications"].append({
                        "subject": v,
                        "institution": request.form.getlist('application_institution')[k],
                        "level": request.form.getlist('application_level')[k]
                    })
                except:
                    pass
        for k,v in enumerate(request.form.getlist('experience_title')):
            if v is not None and len(v) > 0 and v != " ":
                try:
                    rec["experience"].append({
                        "title": v,
                        "brief_description": request.form.getlist('experience_brief_description')[k],
                        "date_from": request.form.getlist('experience_date_from')[k],
                        "date_to": request.form.getlist('experience_date_to')[k]
                    })
                except:
                    pass

        for key in request.form.keys():
            if not key.startswith("qualification_") and not key.startswith("interest_") and not key.startswith("application_") and not key.startswith("experience_") and key not in ['submit']:
                rec[key] = request.form[key]

        if self.id is not None: rec['id'] = self.id
        self.data = rec
        self.save()

    
class School(DomainObject):
    __type__ = 'school'

class Year(DomainObject):
    __type__ = 'year'

class Subject(DomainObject):
    __type__ = 'subject'

class Level(DomainObject):
    __type__ = 'level'

class Grade(DomainObject):
    __type__ = 'grade'

class Institution(DomainObject):
    __type__ = 'institution'

class Advancedlevel(DomainObject):
    __type__ = 'advancedlevel'

class Simd(DomainObject):
    __type__ = 'simd'

    @classmethod
    def makeid(cls):
        if 'post_code' in cls.data:
            return cls.data['post_code'].lower().replace(" ","")
        else:
            return uuid.uuid4().hex

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



# an example account object, which requires the further additional imports
# There is a more complex example below that also requires these imports
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
    def is_admin(self):
        return auth.user.is_admin(self)

    @property
    def view_only(self):
        return auth.user.view_only(self)

    @property
    def is_institution(self):
        return auth.user.is_institution(self)

    @property
    def is_school(self):
        return auth.user.is_school(self)
        
    @property
    def school(self):
        if self.is_school:
            return "Dalkeith" # TODO: this should perhaps be tied more robustly or add a check to school re-names
        else:
            return None
        
    @property
    def institution(self):
        if self.is_institution:
            return "Edinburgh" # TODO as above
        else:
            return None
    
    
# a special object that allows a search onto all index types - FAILS TO CREATE INSTANCES
class Everything(DomainObject):
    __type__ = 'everything'

    @classmethod
    def target(cls):
        t = 'http://' + str(app.config['ELASTIC_SEARCH_HOST']).lstrip('http://').rstrip('/') + '/'
        t += app.config['ELASTIC_SEARCH_DB'] + '/'
        return t


