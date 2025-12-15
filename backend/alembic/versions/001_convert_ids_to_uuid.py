"""convert ids to uuid

Revision ID: 001_convert_ids_to_uuid
Revises: 
Create Date: 14-12-2025 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic.
revision: str = '001_convert_ids_to_uuid'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert INTEGER IDs to UUIDs for users, folders, and files tables."""
    
    connection = op.get_bind()
    
    # Initialize mappings
    user_id_mapping = {}
    folder_id_mapping = {}
    
    # === STEP 1: ADD NEW UUID COLUMNS ===
    op.add_column('users', sa.Column('new_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('folders', sa.Column('new_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('folders', sa.Column('new_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('folders', sa.Column('new_parent_folder_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('files', sa.Column('new_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('files', sa.Column('new_user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('files', sa.Column('new_folder_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # === STEP 2: GENERATE UUIDs FOR USERS ===
    users = connection.execute(sa.text("SELECT id FROM users")).fetchall()
    for row in users:
        old_id = row[0]
        new_uuid = uuid.uuid4()
        user_id_mapping[old_id] = new_uuid
        connection.execute(
            sa.text("UPDATE users SET new_id = CAST(:uuid AS uuid) WHERE id = :old_id"),
            {"uuid": str(new_uuid), "old_id": old_id}
        )
    
    # === STEP 3: GENERATE UUIDs FOR FOLDERS ===
    folders = connection.execute(sa.text("SELECT id, user_id, parent_folder_id FROM folders")).fetchall()
    for row in folders:
        old_id, old_user_id, old_parent_id = row[0], row[1], row[2]
        new_uuid = uuid.uuid4()
        folder_id_mapping[old_id] = new_uuid
        new_user_uuid = user_id_mapping.get(old_user_id)
        new_parent_uuid = folder_id_mapping.get(old_parent_id) if old_parent_id else None
        
        connection.execute(
            sa.text("""
                UPDATE folders 
                SET new_id = CAST(:uuid AS uuid),
                    new_user_id = CAST(:user_uuid AS uuid),
                    new_parent_folder_id = CASE 
                        WHEN :parent_uuid IS NOT NULL THEN CAST(:parent_uuid AS uuid) 
                        ELSE NULL 
                    END
                WHERE id = :old_id
            """),
            {
                "uuid": str(new_uuid),
                "user_uuid": str(new_user_uuid) if new_user_uuid else None,
                "parent_uuid": str(new_parent_uuid) if new_parent_uuid else None,
                "old_id": old_id
            }
        )
    
    # === STEP 4: GENERATE UUIDs FOR FILES ===
    files = connection.execute(sa.text("SELECT id, user_id FROM files")).fetchall()
    for row in files:
        old_id, old_user_id = row[0], row[1]
        new_uuid = uuid.uuid4()
        new_user_uuid = user_id_mapping.get(old_user_id)
        
        connection.execute(
            sa.text("""
                UPDATE files 
                SET new_id = CAST(:uuid AS uuid),
                    new_user_id = CAST(:user_uuid AS uuid)
                WHERE id = :old_id
            """),
            {
                "uuid": str(new_uuid),
                "user_uuid": str(new_user_uuid) if new_user_uuid else None,
                "old_id": old_id
            }
        )
    
    # === STEP 5: DROP CONSTRAINTS AND INDEXES USING RAW SQL WITH IF EXISTS ===
    # This won't fail if they don't exist
    connection.execute(sa.text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS folders_user_id_fkey"))
    connection.execute(sa.text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS folders_parent_folder_id_fkey"))
    connection.execute(sa.text("ALTER TABLE files DROP CONSTRAINT IF EXISTS files_user_id_fkey"))
    connection.execute(sa.text("ALTER TABLE files DROP CONSTRAINT IF EXISTS files_folder_id_fkey"))
    
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_users_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folders_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folders_user_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folders_parent_folder_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folder_user_parent_name"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_files_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_files_user_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_files_folder_id"))
    
    # === STEP 6: SWAP COLUMNS FOR USERS ===
    connection.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pkey"))
    op.drop_column('users', 'id')
    op.alter_column('users', 'new_id', new_column_name='id', nullable=False)
    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_index('ix_users_id', 'users', ['id'])
    
    # === STEP 7: SWAP COLUMNS FOR FOLDERS ===
    connection.execute(sa.text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS folders_pkey"))
    op.drop_column('folders', 'id')
    op.drop_column('folders', 'user_id')
    op.drop_column('folders', 'parent_folder_id')
    op.alter_column('folders', 'new_id', new_column_name='id', nullable=False)
    op.alter_column('folders', 'new_user_id', new_column_name='user_id', nullable=False)
    op.alter_column('folders', 'new_parent_folder_id', new_column_name='parent_folder_id', nullable=True)
    op.create_primary_key('folders_pkey', 'folders', ['id'])
    op.create_index('ix_folders_id', 'folders', ['id'])
    op.create_index('ix_folders_user_id', 'folders', ['user_id'])
    op.create_index('ix_folders_parent_folder_id', 'folders', ['parent_folder_id'])
    
    # === STEP 8: SWAP COLUMNS FOR FILES ===
    connection.execute(sa.text("ALTER TABLE files DROP CONSTRAINT IF EXISTS files_pkey"))
    op.drop_column('files', 'id')
    op.drop_column('files', 'user_id')
    # Drop folder_name (old schema) if it exists
    connection.execute(sa.text("ALTER TABLE files DROP COLUMN IF EXISTS folder_name"))
    op.alter_column('files', 'new_id', new_column_name='id', nullable=False)
    op.alter_column('files', 'new_user_id', new_column_name='user_id', nullable=False)
    op.alter_column('files', 'new_folder_id', new_column_name='folder_id', nullable=True)
    op.create_primary_key('files_pkey', 'files', ['id'])
    op.create_index('ix_files_id', 'files', ['id'])
    op.create_index('ix_files_user_id', 'files', ['user_id'])
    op.create_index('ix_files_folder_id', 'files', ['folder_id'])
    
    # === STEP 9: RECREATE FOREIGN KEYS ===
    op.create_foreign_key('folders_user_id_fkey', 'folders', 'users', ['user_id'], ['id'])
    op.create_foreign_key('folders_parent_folder_id_fkey', 'folders', 'folders', ['parent_folder_id'], ['id'])
    op.create_foreign_key('files_user_id_fkey', 'files', 'users', ['user_id'], ['id'])
    op.create_foreign_key('files_folder_id_fkey', 'files', 'folders', ['folder_id'], ['id'])
    
    # Recreate unique index for folders
    op.create_index('ix_folder_user_parent_name', 'folders', ['user_id', 'parent_folder_id', 'name'], unique=True)


def downgrade() -> None:
    """Revert back to INTEGER IDs - WARNING: Data loss will occur."""
    
    connection = op.get_bind()
    
    # Drop foreign keys
    connection.execute(sa.text("ALTER TABLE files DROP CONSTRAINT IF EXISTS files_folder_id_fkey"))
    connection.execute(sa.text("ALTER TABLE files DROP CONSTRAINT IF EXISTS files_user_id_fkey"))
    connection.execute(sa.text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS folders_parent_folder_id_fkey"))
    connection.execute(sa.text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS folders_user_id_fkey"))
    
    # Drop indexes
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folder_user_parent_name"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_files_folder_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_files_user_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_files_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folders_parent_folder_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folders_user_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_folders_id"))
    connection.execute(sa.text("DROP INDEX IF EXISTS ix_users_id"))
    
    # Add integer columns
    op.add_column('users', sa.Column('int_id', sa.Integer(), autoincrement=True, nullable=True))
    op.add_column('folders', sa.Column('int_id', sa.Integer(), autoincrement=True, nullable=True))
    op.add_column('folders', sa.Column('int_user_id', sa.Integer(), nullable=True))
    op.add_column('folders', sa.Column('int_parent_folder_id', sa.Integer(), nullable=True))
    op.add_column('files', sa.Column('int_id', sa.Integer(), autoincrement=True, nullable=True))
    op.add_column('files', sa.Column('int_user_id', sa.Integer(), nullable=True))
    op.add_column('files', sa.Column('int_folder_id', sa.Integer(), nullable=True))
    
    # Generate sequential IDs
    users = connection.execute(sa.text("SELECT id FROM users ORDER BY created_at")).fetchall()
    for idx, row in enumerate(users, 1):
        connection.execute(sa.text("UPDATE users SET int_id = :new_id WHERE id = :old_id"), 
                          {"new_id": idx, "old_id": str(row[0])})
    
    folders = connection.execute(sa.text("SELECT id FROM folders ORDER BY created_at")).fetchall()
    for idx, row in enumerate(folders, 1):
        connection.execute(sa.text("UPDATE folders SET int_id = :new_id WHERE id = :old_id"),
                          {"new_id": idx, "old_id": str(row[0])})
    
    files = connection.execute(sa.text("SELECT id FROM files ORDER BY created_at")).fetchall()
    for idx, row in enumerate(files, 1):
        connection.execute(sa.text("UPDATE files SET int_id = :new_id WHERE id = :old_id"),
                          {"new_id": idx, "old_id": str(row[0])})
    
    # Drop primary keys
    connection.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_pkey"))
    connection.execute(sa.text("ALTER TABLE folders DROP CONSTRAINT IF EXISTS folders_pkey"))
    connection.execute(sa.text("ALTER TABLE files DROP CONSTRAINT IF EXISTS files_pkey"))
    
    # Swap columns - users
    op.drop_column('users', 'id')
    op.alter_column('users', 'int_id', new_column_name='id', nullable=False)
    
    # Swap columns - folders
    op.drop_column('folders', 'id')
    op.drop_column('folders', 'user_id')
    op.drop_column('folders', 'parent_folder_id')
    op.alter_column('folders', 'int_id', new_column_name='id', nullable=False)
    op.alter_column('folders', 'int_user_id', new_column_name='user_id', nullable=False)
    op.alter_column('folders', 'int_parent_folder_id', new_column_name='parent_folder_id', nullable=True)
    
    # Swap columns - files
    op.drop_column('files', 'id')
    op.drop_column('files', 'user_id')
    op.drop_column('files', 'folder_id')
    op.alter_column('files', 'int_id', new_column_name='id', nullable=False)
    op.alter_column('files', 'int_user_id', new_column_name='user_id', nullable=False)
    op.alter_column('files', 'int_folder_id', new_column_name='folder_id', nullable=True)
    
    # Create primary keys
    op.create_primary_key('users_pkey', 'users', ['id'])
    op.create_primary_key('folders_pkey', 'folders', ['id'])
    op.create_primary_key('files_pkey', 'files', ['id'])
    
    # Recreate indexes
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_folders_id', 'folders', ['id'])
    op.create_index('ix_folders_user_id', 'folders', ['user_id'])
    op.create_index('ix_folders_parent_folder_id', 'folders', ['parent_folder_id'])
    op.create_index('ix_files_id', 'files', ['id'])
    op.create_index('ix_files_user_id', 'files', ['user_id'])
    op.create_index('ix_files_folder_id', 'files', ['folder_id'])
    
    # Recreate foreign keys
    op.create_foreign_key('folders_user_id_fkey', 'folders', 'users', ['user_id'], ['id'])
    op.create_foreign_key('folders_parent_folder_id_fkey', 'folders', 'folders', ['parent_folder_id'], ['id'])
    op.create_foreign_key('files_user_id_fkey', 'files', 'users', ['user_id'], ['id'])
    op.create_foreign_key('files_folder_id_fkey', 'files', 'folders', ['folder_id'], ['id'])
    op.create_index('ix_folder_user_parent_name', 'folders', ['user_id', 'parent_folder_id', 'name'], unique=True)
