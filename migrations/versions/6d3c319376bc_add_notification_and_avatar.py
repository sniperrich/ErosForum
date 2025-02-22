"""Add notification and avatar

Revision ID: 6d3c319376bc
Revises: 
Create Date: 2025-02-07 17:15:51.887928

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6d3c319376bc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('notification',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('is_read', sa.Boolean(), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.Column('reply_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['reply_id'], ['reply.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('notification')
    # ### end Alembic commands ###
