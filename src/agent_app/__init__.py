"""CLI package for the Shopify Store Ops Assistant."""
"""Programmatic interface for the Shopify Agent application."""

from agent_app.service import (
    build_product_page_draft_prompt,
    create_product_page_draft_agent,
    create_store_ops_agent,
    extract_product_page_draft,
    invoke_product_page_draft_agent,
    invoke_store_ops_agent,
    normalize_product_id,
    validate_product_page_draft_output,
)

__all__ = [
    "build_product_page_draft_prompt",
    "create_product_page_draft_agent",
    "create_store_ops_agent",
    "extract_product_page_draft",
    "invoke_product_page_draft_agent",
    "invoke_store_ops_agent",
    "normalize_product_id",
    "validate_product_page_draft_output",
]
