from portality.core import app

def update(obj,user):
    if obj.__type__ == 'account':
        if is_super(user):
            return True
        else:
            return not user.is_anonymous() and user.id == obj.id
    elif obj.__type__ == 'record':
        if is_super(user):
            return True
        else:
            if 'public' in record.data.get('access',[]):
                return True
            elif 'users' in record.get('access',[]) and not user.is_anonymous():
                return True
            elif not user.is_anonymous() and user.id == record.get('author',''):
                return True
            else:
                return False
    else:
        return False

def is_super(user):
    return not user.is_anonymous() and user.id in app.config['SUPER_USER']

def admin(user):
    # a user that can login to the admin interface and do anything, including create new admins / staff
    pass

def staff(user):
    # someone that can login to admin and do stuff but not make new admins / staff
    pass

def adminview(user):
    # someone who can login to admin and view anything but change nothing
    pass


def is_institute(user):
    # if an institutional user return the istitution name they can access
    # which allows pae submissions and viewing and exporting of students info for people applying to that uni
    # perhaps cascade access from admins too? in which case can access any uni?
    # do we need view-only access to this?
    pass

def is_school(user):
    # if a school user return the school name they can access
    # perhaps cascade access from admins too? in which case can access any school?
    pass



