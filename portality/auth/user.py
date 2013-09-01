from portality.core import app

# used in account management to check if logged in user can edit user details
def update(obj,user):
    if obj.__type__ == 'account':
        if is_super(user):
            return True
        else:
            return not user.is_anonymous() and user.id == obj.id
    else:
        return False


# if super user, can do anything. Only available via app settings
def is_super(user):
    return not user.is_anonymous() and user.id in app.config['SUPER_USER']


# a user that can login to the admin interface and do anything
# except create new accounts or alter app settings
def do_admin(user):
    if user.data.get('do_admin',False):
        return True
    else:
        return is_super(user)


# a user that can login to the admin area and view all content
def view_admin(user):
    if user.data.get('view_admin',False) or user.data.get('do_admin',False):
        return True
    else:
        return is_super(user)


# a user associated to a college
def is_course_manager(user):
    if user.data.get('course',False):
        return user.data['course']
    else:
        return view_admin(user)




