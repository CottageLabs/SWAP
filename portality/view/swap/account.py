import uuid, json, time
from copy import deepcopy

from flask import Blueprint, request, url_for, flash, redirect, abort
from flask import render_template
from flask.ext.login import login_user, logout_user, current_user
from flask.ext.wtf import Form, TextField, TextAreaField, SelectField, BooleanField, PasswordField, HiddenField, validators, ValidationError

from urlparse import urlparse, urljoin

from portality.view.swap.forms import dropdowns
from portality import auth
from portality.core import app
import portality.models as models
import portality.util as util

blueprint = Blueprint('account', __name__)


@blueprint.route('/')
def index():
    if current_user.is_anonymous():
        abort(401)
    if not current_user.is_super:
        return redirect('/account/' + current_user.id)
    users = models.Account.query(q={"query":{"match_all":{}},"sort":{'id.exact':{'order':'asc'}}, "size":100000})
    userstats = {
        "super_user": 0,
        "do_admin": 0,
        "view_admin": 0
    }
    if users['hits']['total'] != 0:
        accs = [models.Account.pull(i['_source']['id']) for i in users['hits']['hits']]
        # explicitly mapped to ensure no leakage of sensitive data. augment as necessary
        users = []
        for acc in accs:
            if acc.id in app.config['SUPER_USER']: userstats['super_user'] += 1
            elif acc.data.get('do_admin',"") != "": userstats["do_admin"] += 1
            elif acc.data.get('view_admin',"") != "": userstats["view_admin"] += 1

            user = {'id':acc.id}
            if 'created_date' in acc.data:
                user['created_date'] = acc.data['created_date']
            users.append(user)
    if util.request_wants_json():
        resp = make_response( json.dumps(users, sort_keys=True, indent=4) )
        resp.mimetype = "application/json"
        return resp
    else:
        return render_template('account/all.html', users=users, userstats=userstats)


@blueprint.route('/<username>', methods=['GET','POST', 'DELETE'])
def username(username):
    acc = models.Account.pull(username)

    if request.method == 'DELETE':
        if not auth.user.update(acc,current_user):
            abort(401)
        if acc: acc.delete()
        return ''
    elif request.method == 'POST':
        if not auth.user.update(acc,current_user):
            abort(401)
        info = request.json
        if info.get('id',False):
            if info['id'] != username:
                acc = models.Account.pull(info['id'])
            else:
                info['api_key'] = acc.data['api_key']
        acc.data = info
        if 'password' in info and not info['password'].startswith('sha1'):
            acc.set_password(info['password'])
        acc.save()
        resp = make_response( json.dumps(acc.data, sort_keys=True, indent=4) )
        resp.mimetype = "application/json"
        return resp
    else:
        if not acc:
            abort(404)
        if util.request_wants_json():
            if not auth.user.update(acc,current_user):
                abort(401)
            resp = make_response( json.dumps(acc.data, sort_keys=True, indent=4) )
            resp.mimetype = "application/json"
            return resp
        else:
            return render_template('account/view.html', account=acc)


def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def get_redirect_target():
    for target in request.args.get('next'), request.referrer:
        if not target:
            continue
        if is_safe_url(target):
            return target

class RedirectForm(Form):
    next = HiddenField()

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        if not self.next.data:
            self.next.data = get_redirect_target() or ''

    def redirect(self, endpoint='index', **values):
        if is_safe_url(self.next.data):
            return redirect(self.next.data)
        target = get_redirect_target()
        return redirect(target or url_for(endpoint, **values))

class LoginForm(RedirectForm):
    username = TextField('Username', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form, csrf_enabled=False)
    if request.method == 'POST' and form.validate():
        password = form.password.data
        username = form.username.data
        user = models.Account.pull(username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            flash('Welcome back.', 'success')
            return form.redirect('index')
        else:
            flash('Incorrect username/password', 'error')
    if request.method == 'POST' and not form.validate():
        flash('Invalid form', 'error')
    return render_template('account/login.html', form=form)

@blueprint.route('/policy', methods=['GET', 'POST'])
def policy():
    if request.method == 'GET':
        return render_template('account/policy.html')
    elif request.method == 'POST':
        user = models.Account.pull(current_user.id)
        if user:
            user.data['agreed_policy'] = True
            user.save()
            flash('Thank you for agreeing to our policy. Please continue.', 'success')
            return redirect(get_redirect_target())
        else:
            flash('There was an error. Please try again.', 'error')


@blueprint.route('/logout')
def logout():
    logout_user()
    flash('You are now logged out', 'success')
    return redirect('/')


def existscheck(form, field):
    test = models.Account.pull(form.w.data)
    if test:
        raise ValidationError('Taken! Please try another.')

class RegisterForm(Form):
    w = TextField('Username', [validators.Length(min=3, max=25),existscheck], description="usernames")
    n = TextField('Email Address', [validators.Length(min=3, max=35), validators.Email(message='Must be a valid email address')])
    s = PasswordField('Password', [
        validators.Required(),
        validators.EqualTo('c', message='Passwords must match')
    ])
    c = PasswordField('Repeat Password')
    swap_locale = SelectField('SWAP locale', choices=[('east','east'),('west','west')])
    view_admin = BooleanField('View admin')
    do_admin = BooleanField('Do admin')

@blueprint.route('/register', methods=['GET', 'POST'])
def register():
    if not app.config.get('PUBLIC_REGISTER',False) and not current_user.is_super:
        abort(401)
    form = RegisterForm(request.form, csrf_enabled=False)
    if request.method == 'POST' and form.validate():
        api_key = str(uuid.uuid4())
        account = models.Account(
            id=form.w.data, 
            email=form.n.data,
            api_key=api_key,
            view_admin = form.view_admin.data,
            do_admin = form.do_admin.data
        )
        account.set_password(form.s.data)
        account.save()
        time.sleep(1)
        flash('Account created for ' + account.id, 'success')
        return redirect('/account')
    if request.method == 'POST' and not form.validate():
        flash('Please correct the errors', 'error')
    return render_template('account/register.html', form=form)

