from base import BaseHandler



class UserHandler(BaseHandler):
    """show summary for a given day"""
    def get(self,user_id):
        user = self.store.user_get(user_id)

        actions = self.store.action_get_recent(100,user_id=user.id)
        self.render('user.html', user=user, actions=actions)

        

