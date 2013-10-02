import urllib

import tornado.web

from base import BaseHandler
from unsourced.models import Article,ArticleURL,Label
from unsourced import util
from unsourced import config


class LookupHandler(BaseHandler):
    """ api to look up an article by url

    returns article details as json
    """

    def get(self):
        lookup_url = self.get_argument('url')
        urls = util.www_or_not(lookup_url)
        q = self.session.query(ArticleURL.article_id).\
            filter(ArticleURL.url.in_(urls))
        arts = self.session.query(Article).\
            filter(Article.id.in_(q)).all()

        if len(arts) == 0:
            submit_url = config.settings.root_url + '/addarticle?' + urllib.urlencode({'url':lookup_url})
            self.finish({'status': 'not_found', 'submit_url': submit_url})
            return

        art = arts[0]

        unsourced_url = config.settings.root_url + art.art_url()

        sources = []
        
        for src in art.sources:
            s = {}
            for f in ('url','title','doi','publication','kind'):
                val = getattr(src,f,None)
                if val is not None and val != '':
                    s[f] = val
            if src.pubdate is not None:
                s['pubdate'] = src.pubdate.isoformat()

            sources.append(s) 

        labels = []
        for l in art.labels:
            labels.append( dict(
                id = l.label.id,
                prettyname = l.label.prettyname,
                description = l.label.description,
                icon_url = config.settings.root_url + l.label.icon_url('m') 
            ) )

        details = {
            'status': 'found',
            'headline': art.headline,
            'permalink': art.permalink,
            'pubdate': art.pubdate.isoformat(),
            'other_urls': [url.url for url in art.urls if url.url != art.permalink],
            'unsourced_url' : unsourced_url,
            'summary_url' : unsourced_url,  # TODO: do a proper summary page!
            'sources' : sources,
            'labels': labels,
            'needs_sourcing': art.needs_sourcing }

        self.finish(details)



class LabelHandler(BaseHandler):
    """ api to get a list of available warning labels

    returns label details as json
    """

    def get(self):

        # dodgy_pr is deprecated
        available = self.session.query(Label).\
            filter(Label.id != 'dodgy_pr').\
            all()

        labels = []
        for l in available:
            labels.append( dict(
               id = l.id,
               prettyname = l.prettyname,
               description = l.description,
               icon_url = config.settings.root_url + l.icon_url('m') 
            ) )
        self.finish({'status':'success','labels':labels});

class LoggedInHandler(BaseHandler):
    """ """
    def get(self):
        logged_in = (self.current_user is not None)
        self.finish({'status':'success','logged_in':logged_in})




handlers = [
    (r'/api/lookup', LookupHandler),
    (r'/api/labels', LabelHandler),
    (r'/api/loggedin', LoggedInHandler),
    ]
