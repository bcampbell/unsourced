import tornado.web
import util
from pprint import pprint


class domain(tornado.web.UIModule):
    def render(self, url):
        return util.domain(url)


class day_overview(tornado.web.UIModule):
    def render(self, date, arts):
        num_sourced = sum((1 for a in arts if len(a.sources)>0))
        return self.render_string("modules/day_overview.html", date=date, arts=arts, num_sourced=num_sourced)

class user(tornado.web.UIModule):
    def render(self, user):
        if user is not None:
            out = u'<a href="/user/%d">%s</a>' % (user.id, user.name)
        else:
            out = u'anonymous'
        return out

class art_link(tornado.web.UIModule):
    def render(self, art):
        return '<a href="/art/%s">%s</a> (%s)' % (art.id, art.headline, util.domain(art.permalink))


class action(tornado.web.UIModule):
    def render(self, act):

        def art_link(art):
            return '<a href="/art/%s">%s</a> (%s)' % (art.id, art.headline, util.domain(art.permalink))

        if act.what == 'art_add' and act.article is not None:
            frag = u'added an article: %s' %(art_link(act.article),)
        elif act.what == 'src_add' and act.article is not None:
            if act.source.kind=='pr':
                thing = u'a press release'
            elif act.source.kind=='paper':
                thing = u'an academic paper'
            else:
                thing = u'a source'

            frag = u'added %s to %s' %(thing,art_link(act.article),)
        else:
            frag = u'' # just suppress
        return frag




class add_source(tornado.web.UIModule):
    def render(self,art):
        return self.render_string('modules/add_source.html',art=art)
