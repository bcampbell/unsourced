import tornado.web
import util

class domain(tornado.web.UIModule):
    def render(self, url):
        return util.domain(url)

class action_list(tornado.web.UIModule):
    def render(self, actions):


        def art_link(art):
            return '<a href="/art/%s">%s</a> (%s)' % (art.id, art.headline, util.domain(art.permalink))

        frags = []
        for act in actions:
            user = act.who.name if act.who is not None else u'anonymous'

            if act.what == 'art_add' and act.article is not None:
                frag = 'added an article: %s' %(art_link(act.article),)
            elif act.what == 'src_add' and act.article is not None:
                frag = 'added a source to %s' %(art_link(act.article),)
            else:
                frag = None # just suppress

            if frag is not None:
                frags.append( "%s: %s %s" % (act.performed, user, frag))

        out = u"<ul>\n" + u''.join(["<li>" + f + "</li>\n" for f in frags]) + "</ul>\n"

        return out

