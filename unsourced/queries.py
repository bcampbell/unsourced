# some helpers for building up queries

from models import Source,Article,Action,Lookup,Tag,TagKind,UserAccount,Comment,article_tags,comment_user_map
from sqlalchemy import Date,not_
from sqlalchemy.sql.expression import cast,func
from sqlalchemy.orm import subqueryload,joinedload


def build_action_query(session, view=None, current_user=None):

    actions = session.query(Action).\
        options(joinedload('article'),joinedload('user'),joinedload('source'),joinedload('comment'),joinedload('label'))

    kinds = ('comment','src_add','art_add','mark_sourced','mark_unsourced','helpreq_open','helpreq_close','label_add','label_remove')

    if view=='interesting':
        # actions performed by other people on articles this user has touched
        arts_of_interest = session.query(Action.article_id).\
            distinct().\
            filter(Action.article_id != None).\
            filter(Action.user==current_user)

        actions = actions.filter(Action.article_id.in_(arts_of_interest)).\
            filter(Action.user!=current_user)

    elif view=='mentions':
        # comments aimed at this user
        subq = session.query(comment_user_map.c.comment_id).\
            filter(comment_user_map.c.useraccount_id==current_user.id).\
            subquery()
        actions = actions.filter(Action.comment_id.in_(subq))
        kinds = ['comment']

    elif view == 'comments':
        kinds = ['comment']

    actions = actions.filter(Action.what.in_(kinds)).\
            order_by(Action.performed.desc())


    return actions

