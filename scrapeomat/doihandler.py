
import functools
import urlparse
import json
import copy

import tornado.web
from tornado import httpclient

import doihelpers


class Status(object):
    SUCCESS = 0
    BAD_REQ = 1
    BAD_URL = 2
    NET_ERROR = 3
    NO_DOI_ON_PAGE = 4
    DOI_NOT_FOUND = 5



class DOIHandler(tornado.web.RequestHandler):

    def done(self,status,**kwargs):

        results = {'status':status}
        results.update(kwargs)

        self.write(results)
        self.finish()



    @tornado.web.asynchronous
    def get(self):
        url = self.get_argument("url", None)
        if url is None:
            self.done(Status.BAD_REQ,msg="Missing url")
            return


        o = urlparse.urlparse(url)
        scheme = o.scheme.lower()
        if scheme == 'doi':
            doi = o.path
            self.fetch_by_doi(doi)
            return
        elif scheme in ('http','https'):
            # TODO: some sites (eg scopus.com) do redirects and cookie checks. Gah.
            # To fetch pages we need to follow the redirects and collect the cookies.
            # There is some talk about this on the tornado mailing list (and even a
            # patch to do it).
            # but for now we just won't bother.
            http = tornado.httpclient.AsyncHTTPClient()
            http.fetch(url, callback=self.on_got_page)
        else:
            self.done(Status.BAD_URL,msg="url has bad scheme '%s'"%(scheme,))


    def fetch_by_doi(self,doi):
        # look up metadata using the doi
        dx_url = 'http://dx.doi.org/' + doi
        headers = {'Accept': 'application/rdf+xml'}
        http = tornado.httpclient.AsyncHTTPClient()
        req = tornado.httpclient.HTTPRequest(dx_url,headers=headers)
        self.doi = doi  # save for on_got_rdfxml
        http.fetch(req, callback=self.on_got_rdfxml)


    def on_got_page(self,response):
        # got an html page to scrape for a DOI

        # a lot of sites seem to return a 401 but with valid content
        # (I guess to indicate a summary of a paper you need to pay for)

        if response.error and response.code != 401:
            self.done(Status.NET_ERROR, msg="(http code: %d)" %(response.code,))
            return
        html = response.body
        doi = doihelpers.find_doi(html)
        if doi is not None:
            self.fetch_by_doi(doi)
        else:
            self.done(Status.NO_DOI_ON_PAGE)



    def on_got_rdfxml(self,response):

        # tornado http client follows 301 and 302 redirects.
        # But not 303, which a lot of sites use for serving up RDF data
        # TODO: should tornado automatically follow 303s (and other 3xx codes?)
        if response.code == 303:
            old_req = response.request
            new_url = urlparse.urljoin(old_req.url, response.headers["Location"])
            http = tornado.httpclient.AsyncHTTPClient()
            req = tornado.httpclient.HTTPRequest(new_url,headers=old_req.headers, max_redirects=old_req.max_redirects-1)
            http.fetch(req, callback=self.on_got_rdfxml)
            return

        # might be bad doi, or just not yet on dx.org
        if response.code == 404:
            self.done(Status.DOI_NOT_FOUND)
            return

        content_type = response.headers['content-type']
        content_type = content_type.split(";", 1)[0]
        assert content_type == 'application/rdf+xml'

        rdfxml = response.body
        mt = doihelpers.parseit(rdfxml, self.doi)
        mt['doi'] = self.doi

        self.done(Status.SUCCESS, metadata=mt)

