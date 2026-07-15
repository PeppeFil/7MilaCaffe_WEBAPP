"""close Supabase Data API access to application tables

Revision ID: a7c8d9e0f1b2
Revises: f3a4b5c6d7e8
Create Date: 2026-07-15 23:45:00.000000

"""
from alembic import op


revision = "a7c8d9e0f1b2"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


DATA_API_ROLES = "anon, authenticated, service_role"


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # The Flask application connects directly as the database role configured in
    # DATABASE_URL. These grants are only for Supabase REST/GraphQL Data API roles.
    op.execute(
        f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {DATA_API_ROLES}"
    )
    op.execute(
        f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {DATA_API_ROLES}"
    )
    op.execute(
        "REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public "
        "FROM anon, authenticated, service_role, PUBLIC"
    )

    # Prevent future Alembic-created objects from being exposed automatically.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        f"REVOKE ALL PRIVILEGES ON TABLES FROM {DATA_API_ROLES}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        f"REVOKE ALL PRIVILEGES ON SEQUENCES FROM {DATA_API_ROLES}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        "REVOKE EXECUTE ON FUNCTIONS FROM anon, authenticated, service_role, PUBLIC"
    )

    # Defense in depth: with no policies, Data API roles cannot read any row even
    # if a grant is accidentally restored later. The direct postgres connection
    # used by the server remains unaffected.
    op.execute(
        """
        DO $$
        DECLARE
            table_record record;
        BEGIN
            FOR table_record IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format(
                    'ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY',
                    table_record.tablename
                );
            END LOOP;
        END
        $$
        """
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        DO $$
        DECLARE
            table_record record;
        BEGIN
            FOR table_record IN
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
            LOOP
                EXECUTE format(
                    'ALTER TABLE public.%I DISABLE ROW LEVEL SECURITY',
                    table_record.tablename
                );
            END LOOP;
        END
        $$
        """
    )

    op.execute(
        f"GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO {DATA_API_ROLES}"
    )
    op.execute(
        f"GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO {DATA_API_ROLES}"
    )
    op.execute(
        f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {DATA_API_ROLES}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        f"GRANT ALL PRIVILEGES ON TABLES TO {DATA_API_ROLES}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        f"GRANT ALL PRIVILEGES ON SEQUENCES TO {DATA_API_ROLES}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public "
        f"GRANT EXECUTE ON FUNCTIONS TO {DATA_API_ROLES}"
    )
