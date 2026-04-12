"""Initial schema — all tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # app_settings
    op.create_table("app_settings",
        sa.Column("key",         sa.String(128), primary_key=True),
        sa.Column("value",       sa.JSON,        nullable=True),
        sa.Column("description", sa.Text,        nullable=True),
        sa.Column("updated_at",  sa.DateTime,    server_default=sa.func.now()),
    )
    # enabled_modules
    op.create_table("enabled_modules",
        sa.Column("name",        sa.String(64),   primary_key=True),
        sa.Column("enabled",     sa.Boolean,      nullable=False, server_default="true"),
        sa.Column("config",      sa.JSON,         nullable=True),
        sa.Column("description", sa.Text,         nullable=True),
        sa.Column("updated_at",  sa.DateTime,     server_default=sa.func.now()),
    )
    # broker_connectors
    op.create_table("broker_connectors",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("name",         sa.String(64),  nullable=False, unique=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("adapter_class",sa.String(256), nullable=False),
        sa.Column("status",       sa.String(12),  server_default="disconnected"),
        sa.Column("config",       sa.JSON,        nullable=True),
        sa.Column("enabled",      sa.Boolean,     server_default="false"),
        sa.Column("is_default",   sa.Boolean,     server_default="false"),
        sa.Column("trading_mode", sa.String(5),   server_default="paper"),
        sa.Column("market_types", sa.JSON,        nullable=True),
        sa.Column("created_at",   sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime,    server_default=sa.func.now()),
    )
    # watchlists
    op.create_table("watchlists",
        sa.Column("id",         sa.String(36),  primary_key=True),
        sa.Column("name",       sa.String(128), nullable=False),
        sa.Column("is_default", sa.Boolean,     server_default="false"),
        sa.Column("created_at", sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_table("watchlist_symbols",
        sa.Column("id",           sa.String(36), primary_key=True),
        sa.Column("watchlist_id", sa.String(36), sa.ForeignKey("watchlists.id"), nullable=False),
        sa.Column("symbol",       sa.String(32), nullable=False),
        sa.Column("exchange",     sa.String(16), nullable=False),
        sa.Column("market_type",  sa.String(20), server_default="equity"),
        sa.Column("added_at",     sa.DateTime,   server_default=sa.func.now()),
        sa.UniqueConstraint("watchlist_id", "symbol", "exchange"),
    )
    # strategies
    op.create_table("strategies",
        sa.Column("id",          sa.String(36),  primary_key=True),
        sa.Column("name",        sa.String(256), nullable=False),
        sa.Column("description", sa.Text,        nullable=True),
        sa.Column("market_type", sa.String(9),   server_default="equity"),
        sa.Column("dsl",         sa.JSON,        nullable=False),
        sa.Column("is_active",   sa.Boolean,     server_default="true"),
        sa.Column("tags",        sa.JSON,        nullable=True),
        sa.Column("created_at",  sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_table("strategy_versions",
        sa.Column("id",           sa.String(36), primary_key=True),
        sa.Column("strategy_id",  sa.String(36), sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("version",      sa.Integer,    nullable=False),
        sa.Column("dsl_snapshot", sa.JSON,       nullable=False),
        sa.Column("change_notes", sa.Text,       nullable=True),
        sa.Column("created_at",   sa.DateTime,   server_default=sa.func.now()),
        sa.UniqueConstraint("strategy_id", "version"),
    )
    # bots
    op.create_table("bots",
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("name",         sa.String(256), nullable=False),
        sa.Column("strategy_id",  sa.String(36),  sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("connector_id", sa.String(36),  sa.ForeignKey("broker_connectors.id"), nullable=False),
        sa.Column("symbol",       sa.String(32),  nullable=False),
        sa.Column("exchange",     sa.String(16),  nullable=False),
        sa.Column("market_type",  sa.String(9),   server_default="equity"),
        sa.Column("trading_mode", sa.String(5),   server_default="paper"),
        sa.Column("status",       sa.String(7),   server_default="stopped"),
        sa.Column("config",       sa.JSON,        nullable=True),
        sa.Column("risk_config",  sa.JSON,        nullable=True),
        sa.Column("started_at",   sa.DateTime,    nullable=True),
        sa.Column("stopped_at",   sa.DateTime,    nullable=True),
        sa.Column("created_at",   sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime,    server_default=sa.func.now()),
    )
    # orders
    op.create_table("orders",
        sa.Column("id",               sa.String(36),  primary_key=True),
        sa.Column("bot_id",           sa.String(36),  sa.ForeignKey("bots.id"), nullable=True),
        sa.Column("connector_id",     sa.String(36),  sa.ForeignKey("broker_connectors.id"), nullable=False),
        sa.Column("broker_order_id",  sa.String(128), nullable=True),
        sa.Column("symbol",           sa.String(32),  nullable=False),
        sa.Column("exchange",         sa.String(16),  nullable=False),
        sa.Column("market_type",      sa.String(9),   server_default="equity"),
        sa.Column("side",             sa.String(4),   nullable=False),
        sa.Column("order_type",       sa.String(10),  nullable=False),
        sa.Column("quantity",         sa.Float,       nullable=False),
        sa.Column("price",            sa.Float,       nullable=True),
        sa.Column("stop_price",       sa.Float,       nullable=True),
        sa.Column("status",           sa.String(16),  server_default="pending"),
        sa.Column("filled_quantity",  sa.Float,       server_default="0"),
        sa.Column("avg_fill_price",   sa.Float,       nullable=True),
        sa.Column("trading_mode",     sa.String(5),   server_default="paper"),
        sa.Column("tags",             sa.JSON,        nullable=True),
        sa.Column("placed_at",        sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",       sa.DateTime,    server_default=sa.func.now()),
    )
    # positions
    op.create_table("positions",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("symbol",          sa.String(32),  nullable=False),
        sa.Column("exchange",        sa.String(16),  nullable=False),
        sa.Column("market_type",     sa.String(9),   server_default="equity"),
        sa.Column("side",            sa.String(4),   nullable=False),
        sa.Column("quantity",        sa.Float,       nullable=False),
        sa.Column("avg_price",       sa.Float,       nullable=False),
        sa.Column("current_price",   sa.Float,       nullable=True),
        sa.Column("unrealized_pnl",  sa.Float,       nullable=True),
        sa.Column("realized_pnl",    sa.Float,       server_default="0"),
        sa.Column("is_open",         sa.Boolean,     server_default="true"),
        sa.Column("trading_mode",    sa.String(5),   server_default="paper"),
        sa.Column("connector_id",    sa.String(36),  sa.ForeignKey("broker_connectors.id"), nullable=False),
        sa.Column("opened_at",       sa.DateTime,    server_default=sa.func.now()),
        sa.Column("closed_at",       sa.DateTime,    nullable=True),
        sa.Column("updated_at",      sa.DateTime,    server_default=sa.func.now()),
    )
    # backtests
    op.create_table("backtests",
        sa.Column("id",              sa.String(36),  primary_key=True),
        sa.Column("strategy_id",     sa.String(36),  sa.ForeignKey("strategies.id"), nullable=False),
        sa.Column("name",            sa.String(256), nullable=True),
        sa.Column("symbol",          sa.String(32),  nullable=False),
        sa.Column("exchange",        sa.String(16),  nullable=False),
        sa.Column("start_date",      sa.DateTime,    nullable=False),
        sa.Column("end_date",        sa.DateTime,    nullable=False),
        sa.Column("timeframe",       sa.String(8),   nullable=False),
        sa.Column("initial_capital", sa.Float,       nullable=False),
        sa.Column("commission_pct",  sa.Float,       server_default="0.03"),
        sa.Column("slippage_pct",    sa.Float,       server_default="0.01"),
        sa.Column("params",          sa.JSON,        nullable=True),
        sa.Column("status",          sa.String(16),  server_default="pending"),
        sa.Column("results",         sa.JSON,        nullable=True),
        sa.Column("trade_log",       sa.JSON,        nullable=True),
        sa.Column("equity_curve",    sa.JSON,        nullable=True),
        sa.Column("error_message",   sa.Text,        nullable=True),
        sa.Column("started_at",      sa.DateTime,    nullable=True),
        sa.Column("completed_at",    sa.DateTime,    nullable=True),
        sa.Column("created_at",      sa.DateTime,    server_default=sa.func.now()),
    )
    # portfolio snapshots
    op.create_table("portfolio_snapshots",
        sa.Column("id",              sa.String(36), primary_key=True),
        sa.Column("date",            sa.DateTime,   nullable=False, index=True),
        sa.Column("total_value",     sa.Float,      nullable=False),
        sa.Column("cash",            sa.Float,      nullable=False),
        sa.Column("positions_value", sa.Float,      nullable=False),
        sa.Column("daily_pnl",       sa.Float,      server_default="0"),
        sa.Column("total_pnl",       sa.Float,      server_default="0"),
        sa.Column("trading_mode",    sa.String(5),  server_default="paper"),
        sa.Column("snapshot_data",   sa.JSON,       nullable=True),
    )
    # risk
    op.create_table("risk_profiles",
        sa.Column("id",                  sa.String(36),  primary_key=True),
        sa.Column("name",                sa.String(128), nullable=False, unique=True),
        sa.Column("max_daily_loss",      sa.Float,       nullable=False),
        sa.Column("max_trade_loss",      sa.Float,       nullable=False),
        sa.Column("max_open_positions",  sa.Integer,     nullable=False),
        sa.Column("max_order_value",     sa.Float,       nullable=False),
        sa.Column("max_margin_pct",      sa.Float,       server_default="80"),
        sa.Column("allowed_hours_start", sa.String(8),   nullable=True),
        sa.Column("allowed_hours_end",   sa.String(8),   nullable=True),
        sa.Column("symbol_blacklist",    sa.JSON,        nullable=True),
        sa.Column("symbol_whitelist",    sa.JSON,        nullable=True),
        sa.Column("is_active",           sa.Boolean,     server_default="false"),
        sa.Column("created_at",          sa.DateTime,    server_default=sa.func.now()),
    )
    op.create_table("risk_events",
        sa.Column("id",          sa.String(36),  primary_key=True),
        sa.Column("event_type",  sa.String(64),  nullable=False),
        sa.Column("severity",    sa.String(16),  server_default="warning"),
        sa.Column("message",     sa.Text,        nullable=False),
        sa.Column("extra_metadata", sa.JSON,     nullable=True),
        sa.Column("occurred_at", sa.DateTime,    server_default=sa.func.now(), index=True),
    )
    # alerts & logs
    op.create_table("alerts",
        sa.Column("id",             sa.String(36),  primary_key=True),
        sa.Column("title",          sa.String(256), nullable=False),
        sa.Column("message",        sa.Text,        nullable=False),
        sa.Column("level",          sa.String(8),   server_default="info"),
        sa.Column("source",         sa.String(64),  nullable=True),
        sa.Column("is_read",        sa.Boolean,     server_default="false"),
        sa.Column("extra_metadata", sa.JSON,        nullable=True),
        sa.Column("created_at",     sa.DateTime,    server_default=sa.func.now(), index=True),
    )
    op.create_table("audit_logs",
        sa.Column("id",          sa.String(36),  primary_key=True),
        sa.Column("action",      sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64),  nullable=True),
        sa.Column("entity_id",   sa.String(64),  nullable=True),
        sa.Column("details",     sa.JSON,        nullable=True),
        sa.Column("ip_address",  sa.String(45),  nullable=True),
        sa.Column("logged_at",   sa.DateTime,    server_default=sa.func.now(), index=True),
    )
    # market_data_connectors
    op.create_table("market_data_connectors",
        sa.Column("id",                sa.String(36),  primary_key=True),
        sa.Column("name",              sa.String(64),  nullable=False, unique=True),
        sa.Column("display_name",      sa.String(128), nullable=False),
        sa.Column("adapter_class",     sa.String(256), nullable=False),
        sa.Column("status",            sa.String(12),  server_default="disconnected"),
        sa.Column("config",            sa.JSON,        nullable=True),
        sa.Column("enabled",           sa.Boolean,     server_default="false"),
        sa.Column("supported_markets", sa.JSON,        nullable=True),
        sa.Column("created_at",        sa.DateTime,    server_default=sa.func.now()),
        sa.Column("updated_at",        sa.DateTime,    server_default=sa.func.now()),
    )
    # fills
    op.create_table("fills",
        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("order_id",   sa.String(36), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("quantity",   sa.Float,      nullable=False),
        sa.Column("price",      sa.Float,      nullable=False),
        sa.Column("commission", sa.Float,      server_default="0"),
        sa.Column("filled_at",  sa.DateTime,   server_default=sa.func.now()),
    )


def downgrade() -> None:
    for t in ["fills","audit_logs","alerts","risk_events","risk_profiles",
              "portfolio_snapshots","backtests","positions","orders","bots",
              "strategy_versions","strategies","watchlist_symbols","watchlists",
              "market_data_connectors","broker_connectors","enabled_modules","app_settings"]:
        op.drop_table(t)
