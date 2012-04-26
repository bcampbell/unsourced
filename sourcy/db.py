from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import config

def engine_url():
    """ construct the sqlalchemy engine connection url """
    eng_url = "mysql+mysqldb://%(user)s:%(password)s@%(host)s/%(db)s?charset=utf8" % {
        'user': config.settings.mysql_user,
        'password': config.settings.mysql_password,
        'host': config.settings.mysql_host,
        'db': config.settings.mysql_database
    }
    return eng_url


def create_session():
    """ helper to simplify tools """
    engine = create_engine(engine_url(), echo=False, pool_recycle=3600)
    Session = sessionmaker(bind=engine)

    session = Session()
    return session

