"""Add created_at to flashcards

Revision ID: 996b6040e9d0
Revises: ca8b73265bea
Create Date: 2024-02-17 19:26:32.278448

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '996b6040e9d0'
down_revision = 'ca8b73265bea'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('flashcard', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('flashcard', schema=None) as batch_op:
        batch_op.drop_column('created_at')

    # ### end Alembic commands ###
