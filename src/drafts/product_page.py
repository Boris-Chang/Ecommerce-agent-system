from __future__ import annotations

import re
from html import unescape
from typing import Any

from integrations.shopify.service import get_product_detail


PRODUCT_ID_RE = re.compile(r"gid://shopify/Product/\d+")
NUMERIC_PRODUCT_ID_RE = re.compile(r"(?<!\d)(\d{8,})(?!\d)")


def extract_product_id(text: str) -> str | None:
    match = PRODUCT_ID_RE.search(text)
    if match:
        return match.group(0)

    numeric_match = NUMERIC_PRODUCT_ID_RE.search(text)
    if numeric_match:
        return f"gid://shopify/Product/{numeric_match.group(1)}"

    return None


def _strip_html(html: str | None) -> str:
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    return " ".join(text.split())


def _get_variants(product: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge["node"] for edge in product.get("variants", {}).get("edges", [])]


def _price_range(variants: list[dict[str, Any]]) -> str | None:
    prices = []
    for variant in variants:
        price = variant.get("price")
        if price is None:
            continue
        try:
            prices.append(float(price))
        except (TypeError, ValueError):
            pass

    if not prices:
        return None
    if min(prices) == max(prices):
        return f"{prices[0]:.2f}"
    return f"{min(prices):.2f} - {max(prices):.2f}"


def _build_issues(product: dict[str, Any], description_text: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    seo = product.get("seo") or {}
    title = product.get("title") or ""
    tags = product.get("tags") or []
    total_inventory = product.get("totalInventory")

    if len(title.strip()) < 12:
        issues.append(
            {
                "issue_type": "weak_title",
                "priority": "medium",
                "explanation": "The current title is short and could carry more product, material, style, or occasion keywords.",
            }
        )

    if len(description_text) < 120:
        issues.append(
            {
                "issue_type": "thin_description",
                "priority": "high",
                "explanation": "The product description is light. Add material, styling scenarios, dimensions, gifting angle, and care notes.",
            }
        )

    if not seo.get("title"):
        issues.append(
            {
                "issue_type": "missing_seo_title",
                "priority": "medium",
                "explanation": "SEO title is empty, which weakens search result relevance and click-through potential.",
            }
        )

    if not seo.get("description"):
        issues.append(
            {
                "issue_type": "missing_seo_description",
                "priority": "medium",
                "explanation": "SEO description is empty, so the product page lacks a controlled search snippet.",
            }
        )

    if not tags:
        issues.append(
            {
                "issue_type": "missing_tags",
                "priority": "low",
                "explanation": "No product tags were found. Tags can support collection rules, search, and merchandising workflows.",
            }
        )

    if total_inventory is not None and total_inventory <= 0:
        issues.append(
            {
                "issue_type": "out_of_stock",
                "priority": "high",
                "explanation": "The product has no available inventory and may need restocking or merchandising review.",
            }
        )

    if not issues:
        issues.append(
            {
                "issue_type": "general_optimization",
                "priority": "low",
                "explanation": "No critical issue was detected, but the product page can still be improved for conversion and SEO.",
            }
        )

    return issues


def generate_product_page_draft(user_input: str) -> dict[str, Any]:
    product_id = extract_product_id(user_input)
    if not product_id:
        raise ValueError("No Shopify product GID found in the request.")

    product = get_product_detail(product_id)
    if product is None:
        raise ValueError(f"Product not found: {product_id}")

    title = product.get("title") or "Untitled product"
    product_type = product.get("productType") or "Product"
    vendor = product.get("vendor") or "Brand"
    handle = product.get("handle")
    variants = _get_variants(product)
    description_text = _strip_html(product.get("descriptionHtml"))
    price_range = _price_range(variants)
    issues = _build_issues(product, description_text)

    material_or_style = product_type if product_type != "Product" else "statement style"
    recommended_title = f"{title} | {material_or_style} by {vendor}"

    return {
        "current_product_snapshot": {
            "product_id": product_id,
            "current_title": title,
            "handle": handle,
            "status": product.get("status"),
            "total_inventory": product.get("totalInventory"),
            "price_range": price_range,
        },
        "diagnosis": {
            "main_issues": issues,
            "overall_assessment": (
                f"{title} has a clear product concept, but the page should improve SEO fields, "
                "conversion-focused copy, and merchandising details before scaling traffic."
            ),
        },
        "title_options": [
            {
                "title": recommended_title,
                "rationale": "Keeps the current product name while adding product type and brand context.",
            },
            {
                "title": f"{title} - {product_type} for Everyday Styling",
                "rationale": "Adds use-case language to make the title more search and conversion friendly.",
            },
            {
                "title": f"{vendor} {title}",
                "rationale": "Leads with the vendor name for brand-led merchandising.",
            },
        ],
        "recommended_title": recommended_title,
        "hero_bullets": [
            f"Designed as a {product_type.lower()} with a distinctive visual style.",
            "Easy to position for gifting, occasion styling, or everyday outfits.",
            "Review imagery, sizing, materials, and care details before publishing final copy.",
        ],
        "product_description_markdown": (
            f"### {recommended_title}\n\n"
            f"{title} is a polished {product_type.lower()} designed for shoppers looking for a distinctive accessory. "
            "Use this page to clearly explain the material, size, styling scenarios, and what makes the product feel special.\n\n"
            "#### Why shoppers may like it\n"
            "- Distinctive look suitable for outfit styling\n"
            "- Strong gifting potential\n"
            "- Clear room for stronger SEO and product storytelling\n\n"
            "#### Suggested next edits\n"
            "- Add exact material and dimensions\n"
            "- Add care instructions\n"
            "- Add occasion-based styling notes\n"
            "- Add shipping and return reassurance near the buy button\n"
        ),
        "seo": {
            "seo_title": f"{title} | {product_type} by {vendor}",
            "seo_description": (
                f"Shop {title}, a {product_type.lower()} from {vendor}. "
                "Review style details, materials, inventory, and product page copy before publishing."
            ),
        },
        "faq": [
            {
                "question": "What occasions is this product best for?",
                "answer": "Position it for everyday styling, gifting, and occasion outfits after confirming the exact product materials and dimensions.",
            },
            {
                "question": "What details should be added before publishing?",
                "answer": "Add material, size, care instructions, shipping reassurance, and clearer lifestyle use cases.",
            },
        ],
        "ad_angles": [
            {
                "angle": "Style upgrade",
                "hook": f"Make your outfit feel more finished with {title}.",
                "reason": "Accessory shoppers often respond to simple styling transformation messages.",
            },
            {
                "angle": "Gift-ready accessory",
                "hook": "A thoughtful accessory pick for someone with a distinctive style.",
                "reason": "Gifting language can broaden the product page and ad audience.",
            },
        ],
        "bundle_suggestions": [
            {
                "bundle_idea": f"Pair {title} with complementary accessories or apparel.",
                "reason": "Bundles can increase average order value when the pairing feels style-led.",
            }
        ],
        "manual_review_checklist": [
            "Verify material, dimensions, weight, and care instructions.",
            "Confirm price and compare-at price strategy.",
            "Add SEO title and SEO description in Shopify.",
            "Check product images for close-up, lifestyle, and scale references.",
            "Review final copy manually before publishing.",
        ],
    }
