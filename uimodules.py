import tornado.web
import util

class domain(tornado.web.UIModule):
    def render(self, url):
        return util.domain(url)

