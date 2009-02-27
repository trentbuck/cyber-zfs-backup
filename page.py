
import string

import html
from html import head, body, title

import auth


def header(content=None):
    logout_link = html.a("Logout", att='href="/auth/logout"')
    if content is None:
        status = auth.login_status()
        if status is None:
            content = ''
        else:
            content = "%s (%s) of %s" % ( status[0], status[1], status[3] )
    menu_bar = string.join([html.a("Status", att='href="/show"'), html.a("Browse", att='href="/browse"')], " | ")
    return html.div(html.span(content + html.nbsp(3) + logout_link + html.nbsp(), att='class="logout"') + html.nbsp() + menu_bar, att='class="header"')

def footer(content="Footer"):
    return html.div(content, att='class="footer"')

css_links = html.link(att='type="text/css" rel="stylesheet" href="/static/zbm.css"') \
    + html.link(att='type="text/css" rel="stylesheet" href="/static/tablesorter.css"')

js_links = html.script(att='type="text/javascript" src="/static/jquery-1.2.6.min.js"') \
    + html.script(att='type="text/javascript" src="/static/jquery.tablesorter.min.js"') \
    + html.script(att='type="text/javascript" src="/static/jquery.growl.js"') \
    + html.script(att='type="text/javascript" src="/static/zbm.js"')

# Default page template.
def page(title, content=""):
    return html.html(
        head(html.title(title) + css_links + js_links)
        + body(header()
            + html.div(content, att='id="main"')
            + footer()))

