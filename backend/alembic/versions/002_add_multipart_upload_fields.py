"""Add multipart upload fields to files table

Revision ID: 002_add_multipart_upload_fields
Revises: 001_convert_ids_to_uuid
Create Date: 2024-12-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '002_add_multipart_upload_fields'
down_revision: Union[str, None] = '001_convert_ids_to_uuid'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('files', sa.Column('upload_id', sa.String(), nullable=True))
    op.add_column('files', sa.Column('total_parts', sa.Integer(), nullable=True))
    op.add_column('files', sa.Column('uploaded_parts_json', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('files', 'uploaded_parts_json')
    op.drop_column('files', 'total_parts')
    op.drop_column('files', 'upload_id')

