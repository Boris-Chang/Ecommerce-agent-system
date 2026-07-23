"""Register the approved business-schema baseline without changing objects.

Revision ID: 20260721_0001
Revises: None
"""

revision = "20260721_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op: the 12 business schemas must already exist and be verified."""


def downgrade() -> None:
    """No-op: baseline ownership remains outside Alembic."""
