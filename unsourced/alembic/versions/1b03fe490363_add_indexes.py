"""add indexes

Revision ID: 1b03fe490363
Revises: 4c4e5c2be6a
Create Date: 2012-05-25 11:22:39.131296

"""

# revision identifiers, used by Alembic.
revision = '1b03fe490363'
down_revision = '4c4e5c2be6a'

from alembic import op
import sqlalchemy as sa


def upgrade():

    op.create_index('idx_action_what', 'action', ['what',])
    op.create_index('idx_action_user_id', 'action', ['user_id',])
    op.create_index('idx_action_article_id', 'action', ['article_id',])

    op.create_index('idx_article_pubdate', 'article', ['pubdate',])

    op.create_index('idx_useraccount_email', 'useraccount', ['email',])
    op.create_index('idx_useraccount_username', 'useraccount', ['username',])


def downgrade():
    op.drop_index('idx_action_what', 'action')
    op.drop_index('idx_action_user_id', 'action')
    op.drop_index('idx_action_article_id', 'action')

    op.drop_index('idx_article_pubdate', 'article')

    op.drop_index('idx_useraccount_email', 'useraccount')
    op.drop_index('idx_useraccount_username', 'useraccount')

