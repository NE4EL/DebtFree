"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    strategies = op.create_table('strategies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=20), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('debts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('debt_type', sa.String(length=20), nullable=False),
    sa.Column('balance', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('annual_rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('min_payment', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('term_months', sa.Integer(), nullable=False),
    sa.Column('start_date', sa.Date(), nullable=True),
    sa.Column('payment_type', sa.String(length=10), nullable=False),
    sa.CheckConstraint("payment_type IN ('annuity', 'diff')", name='ck_debts_payment_type'),
    sa.CheckConstraint('annual_rate BETWEEN 0 AND 100', name='ck_debts_rate'),
    sa.CheckConstraint('balance > 0', name='ck_debts_balance'),
    sa.CheckConstraint('min_payment > 0', name='ck_debts_min_payment'),
    sa.CheckConstraint('term_months BETWEEN 1 AND 600', name='ck_debts_term'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_debts_user_id'), 'debts', ['user_id'], unique=False)
    op.create_table('scenarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('strategy_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('monthly_budget', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('total_paid', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('total_interest', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('months_to_payoff', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scenarios_user_id'), 'scenarios', ['user_id'], unique=False)
    op.create_table('extra_payments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('debt_id', sa.Integer(), nullable=True),
    sa.Column('scenario_id', sa.Integer(), nullable=False),
    sa.Column('pay_month', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('effect', sa.String(length=10), nullable=False),
    sa.Column('is_regular', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['debt_id'], ['debts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_extra_payments_scenario_id'), 'extra_payments', ['scenario_id'], unique=False)
    op.create_table('payment_schedule',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scenario_id', sa.Integer(), nullable=False),
    sa.Column('debt_id', sa.Integer(), nullable=False),
    sa.Column('month_no', sa.Integer(), nullable=False),
    sa.Column('payment', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('principal_part', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('interest_part', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('balance_after', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['debt_id'], ['debts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_schedule_scenario_id'), 'payment_schedule', ['scenario_id'], unique=False)
    op.create_table('scenario_debts',
    sa.Column('scenario_id', sa.Integer(), nullable=False),
    sa.Column('debt_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['debt_id'], ['debts.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['scenario_id'], ['scenarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('scenario_id', 'debt_id')
    )

    # справочник стратегий (п. 2.2 отчёта)
    op.bulk_insert(strategies, [
        {'code': 'avalanche', 'name': 'Лавина',
         'description': 'Свободные деньги направляются на долг с наибольшей ставкой'},
        {'code': 'snowball', 'name': 'Снежный ком',
         'description': 'Свободные деньги направляются на долг с наименьшим остатком'},
        {'code': 'minimum', 'name': 'Только минимальные платежи',
         'description': 'Каждый долг гасится своим минимальным платежом, без перераспределения'},
    ])


def downgrade() -> None:
    op.drop_table('scenario_debts')
    op.drop_index(op.f('ix_payment_schedule_scenario_id'), table_name='payment_schedule')
    op.drop_table('payment_schedule')
    op.drop_index(op.f('ix_extra_payments_scenario_id'), table_name='extra_payments')
    op.drop_table('extra_payments')
    op.drop_index(op.f('ix_scenarios_user_id'), table_name='scenarios')
    op.drop_table('scenarios')
    op.drop_index(op.f('ix_debts_user_id'), table_name='debts')
    op.drop_table('debts')
    op.drop_table('users')
    op.drop_table('strategies')
