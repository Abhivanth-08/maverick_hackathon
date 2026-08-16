from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # MVP convenience: create the SQLAlchemy metadata schema.
    # For regulated production deployment, replace with
    # explicit reviewed migration operations.
    from backend.app.database.session import Base

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade():
    from backend.app.database.session import Base

    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)