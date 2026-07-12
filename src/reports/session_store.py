from datetime import datetime
from typing import Any


_LATEST_REPORT: dict[str, Any] | None = None
_LATEST_REPORT_ID: str | None = None

_LATEST_ACTION_TASKS: dict[str, Any] | None = None
_LATEST_ACTION_TASKS_ID: str | None = None

_LATEST_PRODUCT_PAGE_DRAFT: dict[str, Any] | None = None
_LATEST_PRODUCT_PAGE_DRAFT_ID: str | None = None


def save_latest_report_in_memory(report: dict[str, Any]) -> str:
    """
    将最近一次诊断报告保存在当前 Python 进程内存中。

    注意：程序重启后会丢失。当前 CLI 阶段可以接受。
    """
    global _LATEST_REPORT, _LATEST_REPORT_ID

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_id = f"shopify_diagnosis_{timestamp}"

    _LATEST_REPORT = report
    _LATEST_REPORT_ID = report_id

    return report_id


def get_latest_report_from_memory() -> tuple[str, dict[str, Any]]:
    """获取最近一次诊断报告。"""
    if _LATEST_REPORT is None or _LATEST_REPORT_ID is None:
        raise FileNotFoundError("当前会话中还没有可导出的诊断报告。")

    return _LATEST_REPORT_ID, _LATEST_REPORT


def save_latest_action_tasks_in_memory(action_tasks_payload: dict[str, Any]) -> str:
    """将最近一次运营任务清单保存在当前 Python 进程内存中。"""
    global _LATEST_ACTION_TASKS, _LATEST_ACTION_TASKS_ID

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    action_tasks_id = f"shopify_action_tasks_{timestamp}"

    _LATEST_ACTION_TASKS = action_tasks_payload
    _LATEST_ACTION_TASKS_ID = action_tasks_id

    return action_tasks_id


def get_latest_action_tasks_from_memory() -> tuple[str, dict[str, Any]]:
    """获取最近一次生成的运营任务清单。"""
    if _LATEST_ACTION_TASKS is None or _LATEST_ACTION_TASKS_ID is None:
        raise FileNotFoundError("当前会话中还没有可导出的运营任务清单。")

    return _LATEST_ACTION_TASKS_ID, _LATEST_ACTION_TASKS


def save_latest_product_page_draft_in_memory(
    draft_payload: dict[str, Any],
) -> str:
    """将最近一次商品页优化草稿保存在当前 Python 进程内存中。"""
    global _LATEST_PRODUCT_PAGE_DRAFT, _LATEST_PRODUCT_PAGE_DRAFT_ID

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    draft_id = f"shopify_product_page_draft_{timestamp}"

    _LATEST_PRODUCT_PAGE_DRAFT = draft_payload
    _LATEST_PRODUCT_PAGE_DRAFT_ID = draft_id

    return draft_id


def get_latest_product_page_draft_from_memory() -> tuple[str, dict[str, Any]]:
    """获取最近一次商品页优化草稿。"""
    if _LATEST_PRODUCT_PAGE_DRAFT is None or _LATEST_PRODUCT_PAGE_DRAFT_ID is None:
        raise FileNotFoundError("当前会话中还没有可导出的商品页优化草稿。")

    return _LATEST_PRODUCT_PAGE_DRAFT_ID, _LATEST_PRODUCT_PAGE_DRAFT
