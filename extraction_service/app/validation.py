from typing import Optional

from .schema import InvoiceExtraction

# Tolerance for "reasonably matches": whichever is larger of a flat cent
# amount or a percentage of the value being checked. Loose on purpose --
# this is a sanity check for hallucinated totals, not a bookkeeping audit.
TOLERANCE_ABS = 0.01
TOLERANCE_REL = 0.01  # 1%


def _within_tolerance(a: float, b: float) -> bool:
    diff = abs(a - b)
    threshold = max(TOLERANCE_ABS, TOLERANCE_REL * max(abs(a), abs(b)))
    return diff <= threshold


def check_totals(data: InvoiceExtraction) -> Optional[str]:
    """Sanity-check extracted totals against extracted line items.

    Returns a human-readable warning string if the numbers don't
    reasonably reconcile, or None if they do (or if there isn't
    enough data to check).
    """
    if not data.line_items:
        # Nothing to reconcile against -- can't validate, so don't guess.
        return None

    line_item_sum = sum(item.amount for item in data.line_items)
    tax = data.tax or 0.0
    expected_total = line_item_sum + tax

    if not _within_tolerance(expected_total, data.total):
        return (
            f"Sum of line items ({line_item_sum:.2f}) plus tax ({tax:.2f}) = "
            f"{expected_total:.2f}, which does not match the extracted total "
            f"({data.total:.2f}). Please verify against the source document."
        )

    if data.subtotal is not None and not _within_tolerance(data.subtotal, line_item_sum):
        return (
            f"Extracted subtotal ({data.subtotal:.2f}) does not match the sum "
            f"of line item amounts ({line_item_sum:.2f}). Please verify against "
            f"the source document."
        )

    return None
