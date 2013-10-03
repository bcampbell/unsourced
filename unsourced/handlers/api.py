import urllib
import datetime

import tornado.web

from base import BaseHandler
from unsourced.models import Article,ArticleURL,Label,ArticleLabel,Action
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


class AddLabelHandler(BaseHandler):
    """ API call to add a label to a URL
    
    status: 'success' or 'not_logged_in'
    labels: (only on success) updated list of labels for this article
    """
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        label_id = self.get_argument('label')
        url = self.get_argument('url')
        #reason = self.get_argument('reason')

        if self.current_user is None:
            self.finish({'status':'not_logged_in'})
            return

        label = self.session.query(Label).get(label_id)
        if label is None:
            raise tornado.web.HTTPError(400) 

        # article already in db?
        art = self.session.query(Article).join(ArticleURL).\
                filter(ArticleURL.url==url).first()

        if art is None:
            # nope. try scraping it.
            params = {'url': url}
            scrape_url = config.settings.scrapeomat + '/scrape?' + urllib.urlencode(params)
            http = tornado.httpclient.AsyncHTTPClient()

            response = yield tornado.gen.Task(http.fetch, scrape_url)

            try:
                art = scrape.process_scraped(url,response);
            except Exception as err:
                # uhoh... we weren't able to scrape it.
                # enter the article with just the url and a fudged datetime
                url_objs = [ArticleURL(url=url),]
                art = Article("", url, datetime.datetime.utcnow(), url_objs)

            # ok, add the new article to the db (with an action)
            user = self.current_user
            if user is None:
                user = self.get_anon_user()
            action = Action('art_add', user, article=art)
            self.session.add(art)
            self.session.add(action)

        # ok, now we can add the label!
        if label not in [l.label for l in art.labels]:

            artlabel = ArticleLabel(creator=self.current_user)
            artlabel.label = label
            artlabel.article = art
            art.labels.append(artlabel)

            self.session.add(Action('label_add', self.current_user, article=art, label=label))

        self.session.commit()

        # all done - send back the updated list of labels
        labels = []
        for l in art.labels:
            labels.append( dict(
                id = l.label.id,
                prettyname = l.label.prettyname,
                description = l.label.description,
                icon_url = config.settings.root_url + l.label.icon_url('m') 
            ) )
        self.finish({'status':'success', 'labels': labels})


handlers = [
    (r'/api/lookup', LookupHandler),
    (r'/api/labels', LabelHandler),
    (r'/api/loggedin', LoggedInHandler),
    (r'/api/addlabel', AddLabelHandler),
    ]
