import datetime

import tornado.web

from base import BaseHandler
from models import Token,UserAccount

class TokenHandler(BaseHandler):
    """ handle tokens, usually sent out via email """

    def get(self, tok_name):
        tok_ok = False

        tok = self.session.query(Token).filter(Token.name==tok_name).first()
        if tok:
            if datetime.datetime.utcnow() < tok.expires:
                tok_ok = True

        if not tok_ok:
            raise tornado.web.HTTPError(404, "This link has been used already, or has expired")

        payload = tok.get_payload_as_dict()
        if payload['op'] == 'register':

            email = payload['email']

            # user already created?
            user = self.session.query(UserAccount).filter(UserAccount.email==email).first()
            if user is not None:
                # yes - just log them in
                self.set_secure_cookie("user", unicode(user.id))
                self.redirect('/welcome')
                return



            hashed_password = payload['hashed_password']

            # default username derived from email address
            username = email.split("@")[0].lower()
            username = UserAccount.calc_unique_username(self.session, username)

            user = UserAccount(username=username,
                email=email,
                hashed_password=hashed_password)
            self.session.add(user)
#            self.session.delete(tok)
            self.session.commit()

            # log them in
            self.set_secure_cookie("user", unicode(user.id))

            self.redirect('/welcome')
            return
        elif payload['op'] == 'login':
            user_id = payload['user_id']
            next = payload.get('next','/')
            self.set_secure_cookie("user", unicode(user_id))
            self.redirect(next)
            return


        raise tornado.web.HTTPError(404)

handlers = [
    (r"/t/([-_a-zA-Z0-9]+)", TokenHandler),
]

