import tornado.web
import util
from pprint import pprint


class formfield(tornado.web.UIModule):
    def render(self, field):
        return self.render_string("modules/formfield.html", field=field)
        


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
            out = u'<a href="/user/%d">%s</a>' % (user.id, user.prettyname)
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

        if act.what == 'tag_add' and act.article is not None:
            frag = u"tagged '%s' as %s" %(art_link(act.article),act.tag.name)
        elif act.what == 'art_add' and act.article is not None:
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
    def render(self,art_id):
        return self.render_string('modules/add_source.html',art=art)


class source(tornado.web.UIModule):
    def render(self,source):

        out = '<a href="%s">%s</a>' % (source.url, source.url)


        can_upvote = True
        can_downvote = True
        if self.current_user is not None:
            action = self.handler.store.user_get_source_vote(self.current_user, source)
            if action is not None:
                if action.what=='src_upvote':
                    can_upvote = False
                if action.what=='src_downvote':
                    can_downvote = False

        upvote_url = "/source/%d/upvote" % (source.id)
        downvote_url = "/source/%d/downvote" % (source.id)

        #out = '<div>%s</div>' % (out,)

        out += '<div class="rating">'

        if source.score != 0:
            out += ' %d points ' % (source.score,)

        if can_upvote:
            out += '[<a href="%s">+</a>]/' % (upvote_url,)
        else:
            out += '[+]/'

        if can_downvote:
            out += '[<a href="%s">-</a>]' % (downvote_url,)
        else:
            out += '[-]'
        out += "</div>"

        if source.score < 0:
            out = '<div class="downvoted">%s</div>' % (out,)
        return out

