
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

        # check for school changes
        old = Student.pull(self.id)
        if old is not None:
            if old.data.get('school',False) != self.data.get('school',False):
                self.data['simd_decile'] = ""
                self.data['simd_quintile'] = ""
                self.data['shep_school'] = ""
                self.data['leaps_category'] = ""
                self.data['local_authority'] = ""
        
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

        if self.data.get('shep_school',False) == "on":
            self.data['shep_school'] = True
        if self.data.get('shep_school',False) == "off":
            self.data['shep_school'] = False                
        if self.data.get('shep_school',False) == 1:
            self.data['shep_school'] = True
        if self.data.get('shep_school',False) == 0:
            self.data['shep_school'] = False          

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
                    try:
                        appid = request.form.getlist('application_appid')[k]
                        if appid == "": appid = Student.makeid()
                    except:
                        appid = Student.makeid()
                    rec["applications"].append({
                        "subject": v,
                        "institution": request.form.getlist('application_institution')[k],
                        "level": request.form.getlist('application_level')[k],
                        "appid":appid
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

    @classmethod
    def prep(cls, rec):
        if 'id' in rec:
            id_ = rec['id'].strip()
        else:
            id_ = cls.makeid()
            rec['id'] = id_
        
        rec['last_updated'] = datetime.now().strftime("%Y-%m-%d %H%M")

        if 'created_date' not in rec:
            rec['created_date'] = datetime.now().strftime("%Y-%m-%d %H%M")
            
        if 'author' not in rec:
            try:
                rec['author'] = current_user.id
            except:
                rec['author'] = "anonymous"

        if rec.get('shep_school',False) == "on":
            rec['shep_school'] = True
        if rec.get('shep_school',False) == "off":
            rec['shep_school'] = False                
        if rec.get('shep_school',False) == 1:
            rec['shep_school'] = True
        if rec.get('shep_school',False) == 0:
            rec['shep_school'] = False          
        return rec

    def save(self):
        self.data = self.prep(self.data)
        
        old = self.pull(self.id)

        if old is not None:
            # remove any old accounts
            for oc in old.data.get('contacts',[]):
                if oc.get('email',"") not in [o.get('email',False) for o in self.data.get('contacts',[])]:
                    oldaccount = Account.pull(oc.get('email',""))
                    if oldaccount is not None: oldaccount.delete()
            
            # change school name on related accounts if any            
            if old.data.get('name',False) != self.data.get('name',False):
                res = Account.query(q={"query":{"term":{self.__type__+app.config['FACET_FIELD']:old.data['name']}}})
                for aid in [i['_source']['id'] for i in res.get('hits',{}).get('hits',[])]:
                    ua = Account.pull(aid)
                    if ua is not None and self.data.get('name',False):
                        ua.data[self.__type__] = self.data['name']
                        ua.save()

        for c in self.data.get('contacts',[]):
            # create any new accounts
            if c.get('email',"") != "" and ( old is None or c.get('email',"") not in [o.get('email',False) for o in old.data.get('contacts',[])] ):
                account = Account.pull(c['email'])
                if account is None:
                    account = Account(
                        id=c['email'], 
                        email=c['email']
                    )
                    account.data[self.__type__] = self.data.get('name',"")
                    account.set_password(c.get('password',"password"))
                    account.save()
            # change any passwords
            elif c.get('email',"") != "" and c.get('password',"") != "":
                account = Account.pull(c['email'])
                account.set_password(self.data['password'])
                account.save()
                c['password'] = ""

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))

    def delete(self):
        # delete contact accounts
        for c in self.data.get('contacts',[]):
            if c['email'] != "":
                exists = Account.pull(c['email'])
                if exists is not None:
                    exists.delete()
        r = requests.delete(self.target() + self.id)


class Institution(School):
    __type__ = 'institution'

class Subject(DomainObject):
    __type__ = 'subject'

class Level(DomainObject):
    __type__ = 'level'

class Grade(DomainObject):
    __type__ = 'grade'

class Advancedlevel(DomainObject):
    __type__ = 'advancedlevel'

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
    def is_institution(self):
        return auth.user.is_institution(self)

    @property
    def is_school(self):
        return auth.user.is_school(self)
            
    @property
    def agreed_policy(self):
        if not isinstance(self.is_school,bool) or not isinstance(self.is_institution,bool):
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


