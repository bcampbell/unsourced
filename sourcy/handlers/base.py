import tornado.web

class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        user_id = self.get_secure_cookie("user")
        if user_id is None:
            return None
        return self.store.user_get(user_id)

    @property
    def store(self):
        return self.application.store
