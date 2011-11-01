from tornado import httpclient
import logging
import decruft
import metareadability
import pickle

http_client = httpclient.HTTPClient()

cached = {}

try:
    f = open('.scrapecache','r')
    cached = pickle.load(f)
    f.close()
    logging.info("scrapecache: loaded %d entries", len(cached))
except:
    logging.warn("couldn't load scrapecache")
    pass

def scrape(url):
    try:
        if url in cached:
            logging.info("scrape(%s) - used cached version"%(url,))
            return cached[url]
        logging.info("scrape(%s)"%(url,))
        response = http_client.fetch(url)
        html = response.body
        txt = decruft.Document(html).summary()
        headline,byline,pubdate = metareadability.extract(html,url)

        cached[url] = (txt,headline,byline,pubdate)

        f = open('.scrapecache','w')
        pickle.dump(cached,f)
        f.close()
        return cached[url]

    except httpclient.HTTPError, e:
        logging.error("scrape error (%s):" %(url,), e)
        return None


