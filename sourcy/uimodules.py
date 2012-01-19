import tornado.web
import util
from pprint import pprint
from models import Source,Article,Action

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
            out = u'<a href="/user/%d">%s</a>' % (user.id, user.username)
        else:
            out = u'anonymous'
        return out

class art_link(tornado.web.UIModule):
    def render(self, art):
        return '<a href="/art/%s">%s</a> (%s)' % (art.id, art.headline, util.domain(art.permalink))





class add_source(tornado.web.UIModule):
    def render(self,art_id):
        return self.render_string('modules/add_source.html',art=art)


class source(tornado.web.UIModule):
    def render(self,source, element_type='div'):

        can_upvote = False
        can_downvote = False
        if self.current_user is not None:
            prev_vote = self.handler.session.query(Action).filter_by(what='src_vote',user_id=self.current_user.id, source=source).first()

            if prev_vote is None or prev_vote.value>0:
                can_downvote = True
            if prev_vote is None or prev_vote.value<0:
                can_upvote = True

        info = {'paper': {'icon':'paper_icon.png', 'desc':'Academic paper'},
                'pr': {'icon':'recycle_icon.png', 'desc':'Press release'},
                'other': {'icon':'chain_icon.png', 'desc':'Other link'}}

        return self.render_string("modules/source.html", src=source, can_upvote=can_upvote, can_downvote=can_downvote, element_type=element_type, kind_info=info[source.kind])


class tag(tornado.web.UIModule):
    def render(self, tag, element_type='div'):

        can_upvote = False
        can_downvote = False
        if self.current_user is not None:
            prev_vote = self.handler.session.query(Action).filter_by(what='tag_vote',user_id=self.current_user.id, tag=tag).first()

            if prev_vote is None or prev_vote.value>0:
                can_downvote = True
            if prev_vote is None or prev_vote.value<0:
                can_upvote = True

        return self.render_string("modules/tag.html", tag=tag, can_upvote=can_upvote, can_downvote=can_downvote, element_type=element_type)



class league_table(tornado.web.UIModule):
    def render(self, rows, heading, action_desc):
        return self.render_string('modules/league_table.html',rows=rows, heading=heading, action_desc=action_desc)

