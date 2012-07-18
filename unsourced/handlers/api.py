
import tornado.web



from base import BaseHandler
from unsourced.models import Article,ArticleURL
from unsourced import util

from unsourced import config

class LookupHandler(BaseHandler):
    """ api to look up an article by url

    returns article details as json, or 404 if not found
    """

    def get(self):
        urls = util.www_or_not(self.get_argument('url'))
        q = self.session.query(ArticleURL.article_id).\
            filter(ArticleURL.url.in_(urls))
        arts = self.session.query(Article).\
            filter(Article.id.in_(q)).all()

        if len(arts) == 0:
            raise tornado.web.HTTPError(404, "Article not found")

        art = arts[0]

        unsourced_url = config.settings.root_url + '/' +art.art_url()

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

        details = {'headline': art.headline,
            'permalink': art.permalink,
            'pubdate': art.pubdate.isoformat(),
            'other_urls': [url.url for url in art.urls if url.url != art.permalink],
            'unsourced_url' : unsourced_url,
            'sources' : sources,
            'needs_sourcing': art.needs_sourcing }
        self.finish(details)



handlers = [
    (r'/api/lookup', LookupHandler),
    ]
