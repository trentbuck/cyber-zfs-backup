# -*- encoding: UTF-8 -*-
#
# Form based authentication for CherryPy. Requires the
# Session tool to be loaded.
#

import cherrypy
import urllib
import db
import md5

import html
import page

# Keys stored in session.
USER_NAME = '_cp_username'
USER_FULLNAME = '_cp_fullname'
COMPANY_NAME = '_cp_company'
COMPANY_FULLNAME = '_cp_company_full'

def login_status():
    """ Returns (username, fullname, companyname) if logged in or None if not. """
    username = cherrypy.session.get(USER_NAME)
    if username is None:
        return None
    fullname = cherrypy.session.get(USER_FULLNAME)
    companyname = cherrypy.session.get(COMPANY_FULLNAME)
    return (username, fullname, companyname)

def check_credentials(username, password):
    """Verifies credentials for username and password.
    Returns None on success or a string describing the error on failure"""
    # Adapt to your needs
    hashed_password = md5.md5(password).hexdigest()
    row = db.get1("select u.full_name, c.name, c.long_name from users u, companies c where u.company_name = c.name and username = %(username)s and hashed_password = %(hashed_password)s", vars())
    if row is None:
        return ( "Incorrect username or password.", None )

    return ( None, {
        'full_name':row[0],
        'company_name':row[1],
        'company_fullname':row[2]
    } )
    # An example implementation which uses an ORM could be:
    # u = User.get(username)
    # if u is None:
    #     return u"Username %s is unknown to me." % username
    # if u.password != md5.new(password).hexdigest():
    #     return u"Incorrect password"

def check_auth(*args, **kwargs):
    """A tool that looks in config for 'auth.require'. If found and it
    is not None, a login is required and the entry is evaluated as a list of
    conditions that the user must fulfil."""
    conditions = cherrypy.request.config.get('auth.require', None)
    # format GET params
    get_params = urllib.quote(cherrypy.request.request_line.split()[1])
    if conditions is not None:
        username = cherrypy.session.get(USER_NAME)
        if username:
            cherrypy.request.login = username
            for condition in conditions:
                # A condition is just a callable that returns True or False.
                if not condition():
                    # Send old page as from_page parameter.
                    raise cherrypy.HTTPRedirect("/auth/login?from_page=%s" % get_params)
        else:
            # Send old page as from_page parameter
            raise cherrypy.HTTPRedirect("/auth/login?from_page=%s" % get_params)

cherrypy.tools.auth = cherrypy.Tool('before_handler', check_auth)

def require(*conditions):
    """A decorator that appends conditions to the auth.require config
    variable."""
    def decorate(f):
        if not hasattr(f, '_cp_config'):
            f._cp_config = dict()
        if 'auth.require' not in f._cp_config:
            f._cp_config['auth.require'] = []
        f._cp_config['auth.require'].extend(conditions)
        return f
    return decorate


# Conditions are callables that return True
# if the user fulfills the conditions they define, False otherwise
#
# They can access the current username as cherrypy.request.login
#
# Define those at will however suits the application.

def member_of(groupname):
    def check():
        # replace with actual check if <username> is in <groupname>
        return cherrypy.request.login == 'joe' and groupname == 'admin'
    return check

def name_is(reqd_username):
    return lambda: reqd_username == cherrypy.request.login

# These might be handy

def any_of(*conditions):
    """Returns True if any of the conditions match"""
    def check():
        for c in conditions:
            if c():
                return True
        return False
    return check

# By default all conditions are required, but this might still be
# needed if you want to use it inside of an any_of(...) condition
def all_of(*conditions):
    """Returns True if all of the conditions match"""
    def check():
        for c in conditions:
            if not c():
                return False
        return True
    return check


# Controller to provide login and logout actions

class AuthController(object):

    def on_login(self, username):
        """Called on successful login"""

    def on_logout(self, username):
        """Called on logout"""

    def get_loginform(self, username, msg="Enter login information.", from_page="/"):
        return page.page("ZBM - Login",
            html.h1("Login")
            + html.form(
                html.input(att='type="hidden" name="from_page" value="%s"' % ( from_page ))
                + html.p(msg)
                + html.table(
                    html.tbody(
                        html.tr([
                                html.th("Username:") + html.td(html.input(att='type="text" name="username" value="%s"' % ( username ))),
                                html.th("Password:") + html.td(html.input(att='type="password" name="password"')),
                                html.td(html.input(att='type="submit" value="Login"'),
                                    att='colspan="2"')
                            ]
                        )
                    ),
                    att='class="borderless"'),
                att='name="login" method="post" action="/auth/login"')
            + html.script('document.getElementsByName("username")[0].focus();', att='language="javascript"'))


    @cherrypy.expose
    def login(self, username=None, password=None, from_page="/"):
        if username is None or password is None:
            return self.get_loginform("", from_page=from_page)

        ( error_msg, user ) = check_credentials(username, password)
        if not error_msg is None:
            return self.get_loginform(username, error_msg, from_page)
        else:
            sess = cherrypy.session
            sess[USER_NAME] = cherrypy.request.login = username
            sess[USER_FULLNAME] = user['full_name']
            sess[COMPANY_NAME] = user['company_name']
            sess[COMPANY_FULLNAME] = user['company_fullname']
            self.on_login(username)
            raise cherrypy.HTTPRedirect(from_page or "/")

    @cherrypy.expose
    def logout(self, from_page="/"):
        sess = cherrypy.session
        username = sess.get(USER_NAME, None)
        sess[USER_NAME] = None
        sess[USER_FULLNAME] = None
        sess[COMPANY_NAME] = None
        sess[COMPANY_FULLNAME] = None
        if username:
            cherrypy.request.login = None
            self.on_logout(username)
        raise cherrypy.HTTPRedirect(from_page or "/")

