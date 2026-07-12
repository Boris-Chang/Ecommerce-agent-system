from typing import Literal
from pydantic import BaseModel, Field


class CurrentProductSnapshot(BaseModel):
    product_id: str = Field(description="Shopify product id")
    current_title: str = Field(description="Current product title")
    handle: str | None = Field(default=None, description="Shopify product handle")
    status: str | None = Field(default=None, description="Product status")
    total_inventory: int | None = Field(default=None, description="Current total inventory")
    price_range: str | None = Field(default=None, description="Product price range")


class ProductPageIssue(BaseModel):
    issue_type: str = Field(description="Detected issue type")
    priority: Literal["high", "medium", "low"] = Field(description="Issue priority")
    explanation: str = Field(description="Explanation of the issue")


class ProductPageDiagnosis(BaseModel):
    main_issues: list[ProductPageIssue] = Field(description="Main product page issues")
    overall_assessment: str = Field(description="Overall product page assessment")


class TitleOption(BaseModel):
    title: str = Field(description="Suggested product title")
    rationale: str = Field(description="Why this title is suggested")


class SEOFields(BaseModel):
    seo_title: str = Field(description="Suggested SEO title")
    seo_description: str = Field(description="Suggested SEO description")


class FAQItem(BaseModel):
    question: str = Field(description="FAQ question")
    answer: str = Field(description="FAQ answer")


class AdAngle(BaseModel):
    angle: str = Field(description="Ad angle name")
    hook: str = Field(description="Ad hook")
    reason: str = Field(description="Why this ad angle may work")


class BundleSuggestion(BaseModel):
    bundle_idea: str = Field(description="Bundle idea")
    reason: str = Field(description="Why this bundle may be useful")


class ProductPageDraftOutput(BaseModel):
    current_product_snapshot: CurrentProductSnapshot
    diagnosis: ProductPageDiagnosis

    title_options: list[TitleOption]
    recommended_title: str

    hero_bullets: list[str]
    product_description_markdown: str

    seo: SEOFields
    faq: list[FAQItem]

    ad_angles: list[AdAngle]
    bundle_suggestions: list[BundleSuggestion]

    manual_review_checklist: list[str]