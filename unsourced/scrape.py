import urllib
import collections
import json
import datetime

from unsourced import util,analyser,highlight
from unsourced.forms import EnterArticleForm

from unsourced.models import Article,ArticleURL,Action


class Status:
    """ status codes returned by scrapomat """
    SUCCESS = 0
    NET_ERROR = 1
    BAD_REQ = 2
    PAYWALLED = 3
    PARSE_ERROR = 4




def process_scraped(url,response):
    """ process http response from scrapomat, return an article (or raise exception) """
    scraped_art = None
    enter_form = EnterArticleForm(url=url)
    err_msg = None
    if response.error:
        # scrapomat down :-(
        raise Exception("Sorry, there was a problem reading the article.")

    results = json.loads(response.body)
    if results['status'] != Status.SUCCESS:
        error_messages = {
            Status.PAYWALLED: u"Sorry, that article seems to be behind a paywall.",
            Status.PARSE_ERROR: u"Sorry, we couldn't read the article",
            Status.BAD_REQ: u"Sorry, that URL doesn't look like an article",
            Status.NET_ERROR: u"Sorry, we couldn't read that article - is the URL correct?",
        }
        err_msg = error_messages.get(results['status'],"Unknown error")

        raise Exception(err_msg)


    scraped_art = results['article']
    scraped_art['pubdate'] = datetime.datetime.fromtimestamp(scraped_art['pubdate'])
    # use entry form to validate everything's there (ugh!)
    enter_form.url.data = url
    enter_form.title.data = scraped_art['headline']
    enter_form.pubdate.data = scraped_art['pubdate']
    if not enter_form.validate():
        scraped_art = None
        err_msg = u"Sorry, we weren't able to automatically read all the details"
        raise Exception(err_msg)

    # if we've got this far, we now have all the details needed to load the article into the DB. Yay!
    url_objs = [ArticleURL(url=u) for u in scraped_art['urls']]
    art = Article(scraped_art['headline'],scraped_art['permalink'], scraped_art['pubdate'], url_objs)
    return art





