from tornado.options import define, options
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


def engine_url():
    """ construct the sqlalchemy engine connection url from tornado options """
    eng_url = "mysql+mysqldb://%(user)s:%(password)s@%(host)s/%(db)s?charset=utf8" % {
        'user': options.mysql_user,
        'password': options.mysql_password,
        'host': options.mysql_host,
        'db': options.mysql_database
    }
    return eng_url


def create_session():
    """ helper to simplify tools """
    engine = create_engine(engine_url(), echo=False, pool_recycle=3600)
    Session = sessionmaker(bind=engine)

    session = Session()
    return session

