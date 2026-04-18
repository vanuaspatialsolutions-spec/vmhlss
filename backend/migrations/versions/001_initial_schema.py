"""Initial schema creation with all tables.

Revision ID: 001
Revises: None
Create Date: 2026-04-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('organisation', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('two_factor_enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Create dataset_slots table
    op.create_table(
        'dataset_slots',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('slot_code', sa.String(), nullable=False),
        sa.Column('slot_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('required_for', sa.Text(), nullable=True),
        sa.Column('phase', sa.String(), nullable=False),
        sa.Column('is_compulsory', sa.Boolean(), nullable=False),
        sa.Column('minimum_standard', sa.Text(), nullable=True),
        sa.Column('fallback_source', sa.String(), nullable=True),
        sa.Column('accepted_formats', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('required_attributes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slot_code')
    )
    op.create_index(op.f('ix_dataset_slots_slot_code'), 'dataset_slots', ['slot_code'], unique=True)

    # Create dataset_uploads table
    op.create_table(
        'dataset_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('slot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('organisation', sa.String(), nullable=True),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('stored_filename', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_format', sa.String(), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('upload_timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('qa_status', sa.String(), nullable=True),
        sa.Column('qa_report', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('fix_log', postgresql.ARRAY(postgresql.JSON(astext_type=sa.Text())), nullable=True),
        sa.Column('geometry_type', sa.String(), nullable=True),
        sa.Column('crs_detected', sa.String(), nullable=True),
        sa.Column('crs_assigned', sa.String(), nullable=True),
        sa.Column('coverage_pct', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('data_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('geom_extent', postgresql.GEOMETRY('POLYGON', srid=4326), nullable=True),
        sa.ForeignKeyConstraint(['slot_id'], ['dataset_slots.id'], ),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_dataset_uploads_slot_id'), 'dataset_uploads', ['slot_id'])
    op.create_index(op.f('ix_dataset_uploads_uploaded_by'), 'dataset_uploads', ['uploaded_by'])

    # Create knowledge_base_records table
    op.create_table(
        'knowledge_base_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('subcategory', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('author', sa.String(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('relevance_score', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_knowledge_base_records_category'), 'knowledge_base_records', ['category'])
    op.create_index(op.f('ix_knowledge_base_records_subcategory'), 'knowledge_base_records', ['subcategory'])

    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('analysis_name', sa.String(), nullable=False),
        sa.Column('analysis_type', sa.String(), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('study_area_geom', postgresql.GEOMETRY('MULTIPOLYGON', srid=4326), nullable=False),
        sa.Column('ahp_weight_set', sa.String(), nullable=True),
        sa.Column('custom_weights', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('input_datasets', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_params', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('processing_status', sa.String(), nullable=True),
        sa.Column('processing_log', sa.Text(), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('suitability_raster', sa.String(), nullable=True),
        sa.Column('suitability_classes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('output_geom', postgresql.GEOMETRY('MULTIPOLYGON', srid=4326), nullable=True),
        sa.Column('statistics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('constraints_applied', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('exclusion_masks', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('crs', sa.String(), nullable=True),
        sa.Column('resolution_m', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_archived', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_email', sa.String(), nullable=True),
        sa.Column('user_role', sa.String(), nullable=True),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('resource_type', sa.String(), nullable=True),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('detail', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_log_action_type'), 'audit_log', ['action_type'])
    op.create_index(op.f('ix_audit_log_resource_type'), 'audit_log', ['resource_type'])
    op.create_index(op.f('ix_audit_log_resource_id'), 'audit_log', ['resource_id'])
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'])
    op.create_index(op.f('ix_audit_log_session_id'), 'audit_log', ['session_id'])

    # Create reports table
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('report_name', sa.String(), nullable=False),
        sa.Column('report_type', sa.String(), nullable=False),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('executive_summary', sa.Text(), nullable=True),
        sa.Column('sections', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('findings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('limitations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('statistics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('visualizations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('maps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tables', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('data_sources', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('methodology', sa.Text(), nullable=True),
        sa.Column('crs', sa.String(), nullable=True),
        sa.Column('study_area_geom', postgresql.GEOMETRY('MULTIPOLYGON', srid=4326), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('distribution_list', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('access_level', sa.String(), nullable=True),
        sa.Column('report_file_path', sa.String(), nullable=True),
        sa.Column('attachments', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['analysis_id'], ['analyses.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_report_type'), 'reports', ['report_type'])
    op.create_index(op.f('ix_reports_analysis_id'), 'reports', ['analysis_id'])

    # Create vanuatu_places table
    op.create_table(
        'vanuatu_places',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('name_bi', sa.String(), nullable=True),
        sa.Column('place_type', sa.String(), nullable=True),
        sa.Column('island', sa.String(), nullable=True),
        sa.Column('province', sa.String(), nullable=True),
        sa.Column('geom', postgresql.GEOMETRY('POINT', srid=4326), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create ahp_weights table
    op.create_table(
        'ahp_weights',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('weight_set_name', sa.String(), server_default='default', nullable=True),
        sa.Column('assessment_type', sa.String(), nullable=True),
        sa.Column('criteria_key', sa.String(), nullable=True),
        sa.Column('weight', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create audit_log immutable trigger
    op.execute("""
    CREATE OR REPLACE FUNCTION prevent_audit_modification()
    RETURNS TRIGGER AS $$
    BEGIN
        RAISE EXCEPTION 'Audit log is immutable. Records cannot be modified or deleted.';
    END;
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    CREATE TRIGGER audit_log_immutable
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS prevent_audit_modification()")

    # Drop tables in reverse order of creation
    op.drop_table('ahp_weights')
    op.drop_table('vanuatu_places')
    op.drop_index(op.f('ix_reports_analysis_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_report_type'), table_name='reports')
    op.drop_table('reports')
    op.drop_index(op.f('ix_audit_log_session_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_user_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_resource_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_resource_type'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_action_type'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_table('analyses')
    op.drop_index(op.f('ix_knowledge_base_records_subcategory'), table_name='knowledge_base_records')
    op.drop_index(op.f('ix_knowledge_base_records_category'), table_name='knowledge_base_records')
    op.drop_table('knowledge_base_records')
    op.drop_index(op.f('ix_dataset_uploads_uploaded_by'), table_name='dataset_uploads')
    op.drop_index(op.f('ix_dataset_uploads_slot_id'), table_name='dataset_uploads')
    op.drop_table('dataset_uploads')
    op.drop_index(op.f('ix_dataset_slots_slot_code'), table_name='dataset_slots')
    op.drop_table('dataset_slots')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
