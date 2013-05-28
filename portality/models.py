
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
        
        if 'status' not in self.data:
            # TODO: ensure this sets first status to the correct one
            self.data['status'] = 'new'

        if 'SIMD_decile' not in self.data:
            s = models.Simd.pull(self.data['post_code'])
            if s is not None:
                self.data['SIMD_decile'] = s.data.get('SIMD_decile','SIMD decile missing')
                self.data['SIMD_quintile'] = s.data.get('SIMD_quintile','SIMD quintile missing')
            else:
                self.data['SIMD_decile'] = 'SIMD data for post code missing'
                self.data['SIMD_quintile'] = 'SIMD data for post code missing'

        if 'LEAPS_category' not in self.data:
            s = models.School.query(q={'query':{'term':{'name.exact':self.data['school']}}})
            if s.get('hits',{}).get('total',0) == 0:
                self.data['LEAPS_category'] = "unknown"
                self.data['SHEP_school'] = "unknown"
            else:
                self.data['LEAPS_category'] = s.get('hits',{}).get('hits',[])[0]['_source'].get('LEAPS_category','unknown')
                self.data['SHEP_school'] = s.get('hits',{}).get('hits',[])[0]['_source'].get('SHEP_school','unknown')

        r = requests.post(self.target() + self.data['id'], data=json.dumps(self.data))

    
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
    
    # note SIMD should have their ID as the post code with all blank spaces removed
    # or else need a method to retrieve by post code and change the calls in the student save model



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
    
    
# a special object that allows a search onto all index types - FAILS TO CREATE INSTANCES
class Everything(DomainObject):
    __type__ = 'everything'

    @classmethod
    def target(cls):
        t = 'http://' + str(app.config['ELASTIC_SEARCH_HOST']).lstrip('http://').rstrip('/') + '/'
        t += app.config['ELASTIC_SEARCH_DB'] + '/'
        return t


