
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

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))


    def save_from_form(self, request):
        rec = {}
        
        for key in request.form.keys():
            if key not in ['submit']:
                rec[key] = request.form[key]

        if self.id is not None: rec['id'] = self.id
        self.data = rec
        self.save()

    
class College(DomainObject):
    __type__ = 'college'

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


class University(College):
    __type__ = 'university'


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
    def is_university(self):
        return auth.user.is_university(self)

    @property
    def is_college(self):
        return auth.user.is_college(self)
            
    @property
    def agreed_policy(self):
        if not isinstance(self.is_college,bool) or not isinstance(self.is_university,bool):
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


