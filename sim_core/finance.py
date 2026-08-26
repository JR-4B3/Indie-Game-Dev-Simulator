"""Standalone finance primitives for the simulation core.

The helpers in this module deliberately use attribute access instead of
importing the simulation's concrete ``Studio`` type.  They therefore work with
save adapters, test doubles, and older studios that expose only some fields.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date as date_type, datetime
import math
from typing import Any, Literal


TransactionKind = Literal["operating", "investing", "financing", "transfer"]
TRANSACTION_KINDS = frozenset(("operating", "investing", "financing", "transfer"))
WEEKS_PER_MONTH = 52.0 / 12.0


@dataclass
class Transaction:
    """A cash-ledger entry.

    ``amount`` is the positive magnitude of the transaction. ``cash_delta``
    carries its sign, which allows financing and transfers to remain outside
    operating profit and loss.
    """

    transaction_id: int
    date: str
    kind: TransactionKind
    category: str
    amount: float
    cash_delta: float
    game_id: int | str | None = None
    counterparty: str = ""
    memo: str = ""


def _number(value: Any, default: float = 0.0) -> float:
    """Return a finite numeric value without accepting booleans."""
    if callable(value):
        try:
            value = value()
        except TypeError:
            return default
    if isinstance(value, bool):
        return default
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _required_amount(value: Any, name: str) -> float:
    amount = _number(value, float("nan"))
    if not math.isfinite(amount) or amount < 0:
        raise ValueError(f"{name} must be a finite, non-negative number")
    return amount


def _date_text(owner: Any, value: Any) -> str:
    if value is None:
        for name in ("current_date", "date", "accounting_date", "accounting_month"):
            if hasattr(owner, name):
                value = getattr(owner, name)
                if value is not None:
                    break
        else:
            clock = getattr(owner, "clock", None)
            value = getattr(clock, "current_date", "") if clock is not None else ""
    if isinstance(value, (datetime, date_type)):
        return value.isoformat()
    return str(value) if value is not None else ""


def _record_value(record: Any, name: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(name, default)
    return getattr(record, name, default)


def _identifier(value: Any) -> int | str | None:
    if value is None or isinstance(value, (int, str)):
        return value
    return str(value)


def _next_record_id(studio: Any) -> int:
    records = getattr(studio, "transactions", ()) or ()
    highest = 0
    for record in records:
        value = _record_value(record, "transaction_id", 0)
        if isinstance(value, int) and not isinstance(value, bool):
            highest = max(highest, value)

    if hasattr(studio, "next_transaction_id"):
        candidate = getattr(studio, "next_transaction_id")
        if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate > 0:
            return max(candidate, highest + 1)
    return highest + 1


def _append_existing(owner: Any, name: str, record: dict[str, Any]) -> None:
    """Append to a collection without adding an absent compatibility field."""
    if not hasattr(owner, name):
        return
    collection = getattr(owner, name)
    if collection is None:
        setattr(owner, name, [record])
        return
    append = getattr(collection, "append", None)
    if callable(append):
        append(record)
        return
    try:
        setattr(owner, name, [*collection, record])
    except TypeError as exc:
        raise TypeError(f"{name} must be an appendable collection") from exc


def record_transaction(
    studio: Any,
    date: Any = None,
    kind: TransactionKind = "operating",
    category: str = "",
    amount: float = 0.0,
    cash_delta: float = 0.0,
    game_id: int | str | None = None,
    counterparty: str = "",
    memo: str = "",
) -> dict[str, Any]:
    """Build and, when supported, append a serializable transaction record.

    The helper never creates ``transactions`` or ``next_transaction_id`` on an
    older studio.  If those attributes already exist, it appends to the former
    and advances the latter.
    """
    if kind not in TRANSACTION_KINDS:
        allowed = ", ".join(sorted(TRANSACTION_KINDS))
        raise ValueError(f"kind must be one of: {allowed}")

    transaction_id = _next_record_id(studio)
    entry = Transaction(
        transaction_id=transaction_id,
        date=_date_text(studio, date),
        kind=kind,
        category=str(category),
        amount=_required_amount(amount, "amount"),
        cash_delta=_number(cash_delta, float("nan")),
        game_id=_identifier(game_id),
        counterparty=str(counterparty),
        memo=str(memo),
    )
    if not math.isfinite(entry.cash_delta):
        raise ValueError("cash_delta must be a finite number")

    record = asdict(entry)
    _append_existing(studio, "transactions", record)
    if hasattr(studio, "next_transaction_id"):
        setattr(studio, "next_transaction_id", transaction_id + 1)
    return record


def _increment_existing(owner: Any, names: Sequence[str], amount: float) -> None:
    for name in names:
        if not hasattr(owner, name):
            continue
        current = getattr(owner, name)
        try:
            setattr(owner, name, current + amount)
        except (AttributeError, TypeError):
            continue


def _increment_categories(owner: Any, names: Sequence[str], category: str, amount: float) -> None:
    seen: set[int] = set()
    for name in names:
        if not hasattr(owner, name):
            continue
        categories = getattr(owner, name)
        if categories is None:
            categories = {}
            setattr(owner, name, categories)
        if not isinstance(categories, MutableMapping) or id(categories) in seen:
            continue
        seen.add(id(categories))
        categories[category] = _number(categories.get(category, 0.0)) + amount


def _change_cash(studio: Any, delta: float) -> None:
    _increment_existing(studio, ("cash",), delta)


def financing_inflow(
    studio: Any,
    amount: float,
    category: str = "Financing",
    *,
    date: Any = None,
    game_id: int | str | None = None,
    counterparty: str = "",
    memo: str = "",
) -> dict[str, Any]:
    """Add financing cash without recognizing operating revenue."""
    value = _required_amount(amount, "amount")
    _change_cash(studio, value)
    return record_transaction(
        studio, date, "financing", category, value, value, game_id, counterparty, memo
    )


def principal_payment(
    studio: Any,
    amount: float,
    category: str = "Debt principal",
    *,
    date: Any = None,
    game_id: int | str | None = None,
    counterparty: str = "",
    memo: str = "",
) -> dict[str, Any]:
    """Pay debt principal from cash without recognizing an operating expense."""
    value = _required_amount(amount, "amount")
    _change_cash(studio, -value)
    return record_transaction(
        studio, date, "financing", category, value, -value, game_id, counterparty, memo
    )


def operating_revenue(
    studio: Any,
    amount: float,
    category: str = "Revenue",
    *,
    date: Any = None,
    game_id: int | str | None = None,
    counterparty: str = "",
    memo: str = "",
) -> dict[str, Any]:
    """Receive cash and recognize revenue in every supported P&L field."""
    value = _required_amount(amount, "amount")
    _change_cash(studio, value)
    _increment_existing(studio, ("current_revenue", "period_revenue", "lifetime_revenue"), value)
    _increment_categories(
        studio,
        ("current_revenue_categories", "period_revenue_categories"),
        category,
        value,
    )
    return record_transaction(
        studio, date, "operating", category, value, value, game_id, counterparty, memo
    )


def operating_expense(
    studio: Any,
    amount: float,
    category: str = "Expense",
    *,
    date: Any = None,
    game_id: int | str | None = None,
    counterparty: str = "",
    memo: str = "",
) -> dict[str, Any]:
    """Spend cash and recognize an expense in every supported P&L field."""
    value = _required_amount(amount, "amount")
    _change_cash(studio, -value)
    _increment_existing(studio, ("current_expenses", "period_expenses", "lifetime_expenses"), value)
    _increment_categories(
        studio,
        ("current_expense_categories", "period_expense_categories"),
        category,
        value,
    )
    return record_transaction(
        studio, date, "operating", category, value, -value, game_id, counterparty, memo
    )


def _first_numeric_attribute(owner: Any, names: Sequence[str]) -> float | None:
    for name in names:
        if not hasattr(owner, name):
            continue
        value = getattr(owner, name)
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
        if isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number):
            return max(0.0, number)
    return None


def _fixed_burn(studio: Any, override: float | None) -> float:
    if override is not None:
        return _required_amount(override, "fixed_burn")

    direct = _first_numeric_attribute(
        studio,
        (
            "fixed_monthly_cost",
            "monthly_fixed_cost",
            "monthly_fixed_burn",
            "monthly_burn",
            "fixed_burn",
        ),
    )
    if direct is not None:
        return direct

    if hasattr(studio, "monthly_cost_breakdown"):
        breakdown = getattr(studio, "monthly_cost_breakdown")
        if callable(breakdown):
            try:
                breakdown = breakdown()
            except TypeError:
                breakdown = None
        if isinstance(breakdown, Mapping):
            return sum(max(0.0, _number(value)) for value in breakdown.values())

    team = getattr(studio, "team", ()) or ()
    salaries = sum(
        max(0.0, _number(_record_value(employee, "monthly_salary", 0.0)))
        for employee in team
    )

    # This structural fallback matches the legacy Studio without importing it.
    if hasattr(studio, "active_sales") and hasattr(studio, "catalog"):
        burden = round(
            sum(
                max(0.0, _number(_record_value(employee, "monthly_salary", 0.0)))
                for employee in team
                if not _record_value(employee, "founder", False)
            )
            * 0.13
        )
        games = {
            _record_value(game, "game_id"): game
            for game in (getattr(studio, "catalog") or ())
        }
        portfolio_operations = 0.0
        for sale in getattr(studio, "active_sales") or ():
            game = games.get(_record_value(sale, "game_id"))
            if game is None or _record_value(game, "support_level", "") == "Sunset":
                continue
            portfolio_operations += (
                50.0 if _record_value(game, "support_level", "") == "Maintenance" else 150.0
            )
        operations = 560.0 + 85.0 * len(team) + portfolio_operations
        upgrade_cost = 0.0
        for upgrade in getattr(studio, "upgrades", ()) or ():
            if isinstance(upgrade, Mapping):
                upgrade_cost += _number(upgrade.get("monthly"))
                upgrade_cost += _number(upgrade.get("per_employee")) * len(team)
            else:
                upgrade_cost += _number(getattr(upgrade, "monthly", 0.0))
                upgrade_cost += _number(getattr(upgrade, "per_employee", 0.0)) * len(team)
        return salaries + burden + operations + upgrade_cost
    return salaries


def _weekly_debt(studio: Any) -> float:
    direct = _first_numeric_attribute(
        studio,
        (
            "weekly_debt_payment",
            "weekly_debt_obligation",
            "weekly_debt",
            "loan_weekly_obligation",
        ),
    )
    if direct is not None:
        return direct

    total = 0.0
    for loan in getattr(studio, "loans", ()) or ():
        balance = _record_value(loan, "balance", None)
        if balance is not None and _number(balance) <= 0:
            continue
        weeks_left = _record_value(loan, "weeks_left", None)
        if weeks_left is not None and _number(weeks_left) <= 0:
            continue
        total += max(0.0, _number(_record_value(loan, "weekly_payment", 0.0)))
    return total


def _category_amount(categories: Any, wanted: str) -> float:
    if not isinstance(categories, Mapping):
        return 0.0
    wanted = wanted.casefold()
    return sum(
        max(0.0, _number(amount))
        for category, amount in categories.items()
        if str(category).casefold() == wanted
    )


def _trailing_hosting(studio: Any, trailing_months: int) -> float:
    direct = _first_numeric_attribute(
        studio,
        (
            "trailing_monthly_hosting",
            "trailing_hosting_cost",
            "monthly_hosting_cost",
            "hosting_monthly_average",
        ),
    )
    if direct is not None:
        return direct

    history = getattr(studio, "hosting_history", None)
    if isinstance(history, Sequence) and not isinstance(history, (str, bytes)) and history:
        values = [max(0.0, _number(item)) for item in history[-trailing_months:]]
        if values:
            return sum(values) / len(values)

    ledger = getattr(studio, "ledger", None)
    if isinstance(ledger, Sequence) and not isinstance(ledger, (str, bytes)) and ledger:
        values = []
        for entry in ledger[:trailing_months]:
            categories = _record_value(entry, "categories", {})
            values.append(_category_amount(categories, "Hosting"))
        if values:
            return sum(values) / len(values)

    grouped: dict[str, float] = {}
    for record in getattr(studio, "transactions", ()) or ():
        category = str(_record_value(record, "category", ""))
        if category.casefold() != "hosting":
            continue
        date = str(_record_value(record, "date", ""))[:7]
        amount = _number(_record_value(record, "amount", 0.0))
        grouped[date] = grouped.get(date, 0.0) + max(0.0, amount)
    if grouped:
        months = sorted(grouped)[-trailing_months:]
        return sum(grouped[month] for month in months) / len(months)

    return _category_amount(getattr(studio, "period_expense_categories", {}), "Hosting")


def _payment_value(payment: Any, name: str, default: Any = None) -> Any:
    if isinstance(payment, Mapping):
        return payment.get(name, default)
    return getattr(payment, name, default)


def _commitment_totals(studio: Any) -> tuple[float, float]:
    one_time = _first_numeric_attribute(
        studio,
        ("committed_one_time_payments", "committed_cash_payments"),
    ) or 0.0
    direct = _first_numeric_attribute(
        studio,
        (
            "committed_monthly_payments",
            "monthly_committed_payments",
            "monthly_commitments",
        ),
    )
    if direct is not None:
        return direct, one_time

    payments = getattr(studio, "committed_payments", ()) or ()
    if isinstance(payments, (int, float)) and not isinstance(payments, bool):
        return max(0.0, _number(payments)), one_time
    if isinstance(payments, Mapping):
        payment_fields = {
            "amount",
            "monthly_amount",
            "monthly_payment",
            "weekly_amount",
            "weekly_payment",
            "frequency",
        }
        if payment_fields.isdisjoint(payments):
            return sum(max(0.0, _number(value)) for value in payments.values()), one_time
        payments = (payments,)

    monthly = 0.0
    for payment in payments:
        if isinstance(payment, (int, float)) and not isinstance(payment, bool):
            monthly += max(0.0, _number(payment))
            continue
        status = str(_payment_value(payment, "status", "active")).casefold()
        if status in {"cancelled", "canceled", "paid", "complete", "completed"}:
            continue
        if _payment_value(payment, "active", True) is False:
            continue
        amount = _payment_value(
            payment,
            "monthly_amount",
            _payment_value(payment, "monthly_payment", None),
        )
        if amount is not None:
            monthly += max(0.0, _number(amount))
            continue
        weekly = _payment_value(
            payment,
            "weekly_amount",
            _payment_value(payment, "weekly_payment", None),
        )
        if weekly is not None:
            monthly += max(0.0, _number(weekly)) * WEEKS_PER_MONTH
            continue
        amount = max(0.0, _number(_payment_value(payment, "amount", 0.0)))
        frequency = str(_payment_value(payment, "frequency", "monthly")).casefold()
        if frequency in {"week", "weekly"}:
            monthly += amount * WEEKS_PER_MONTH
        elif frequency in {"year", "yearly", "annual", "annually"}:
            monthly += amount / 12.0
        elif frequency in {"quarter", "quarterly"}:
            monthly += amount / 3.0
        elif frequency in {"day", "daily"}:
            monthly += amount * 365.0 / 12.0
        elif frequency in {"once", "one-time", "one_time", "single"}:
            one_time += amount
        else:
            monthly += amount
    return monthly, one_time


def committed_monthly_cost(
    studio: Any,
    fixed_burn: float | None = None,
    *,
    trailing_months: int = 3,
) -> float:
    """Return forward monthly burn from fixed, debt, hosting, and commitments.

    ``fixed_burn`` can supply a value calculated by a caller's own rules.  When
    omitted, common numeric fields and the legacy Studio shape are duck-typed.
    The tax reserve is a cash balance, so it is excluded here and reserved by
    :func:`forward_runway_months` instead.
    """
    if trailing_months < 1:
        raise ValueError("trailing_months must be at least 1")
    committed, _ = _commitment_totals(studio)
    monthly_tax = _first_numeric_attribute(
        studio,
        ("committed_monthly_tax", "monthly_tax_payment", "monthly_tax_reserve"),
    )
    return (
        _fixed_burn(studio, fixed_burn)
        + _weekly_debt(studio) * WEEKS_PER_MONTH
        + _trailing_hosting(studio, trailing_months)
        + committed
        + (monthly_tax or 0.0)
    )


def forward_runway_months(
    studio: Any,
    fixed_burn: float | None = None,
    *,
    trailing_months: int = 3,
) -> float:
    """Return months of cash left after tax and one-time commitments.

    A studio with available cash and no committed monthly cost has infinite
    runway.  A studio with no available cash has zero runway.
    """
    cash = max(0.0, _number(getattr(studio, "cash", 0.0)))
    tax_reserve = _first_numeric_attribute(
        studio,
        ("tax_reserve", "reserved_tax", "tax_cash_reserve"),
    ) or 0.0
    _, one_time = _commitment_totals(studio)
    available_cash = max(0.0, cash - tax_reserve - one_time)
    if available_cash <= 0:
        return 0.0
    monthly_cost = committed_monthly_cost(
        studio,
        fixed_burn,
        trailing_months=trailing_months,
    )
    return math.inf if monthly_cost <= 0 else available_cash / monthly_cost


def reconcile_cash(
    studio: Any,
    opening_cash: float | None = None,
    *,
    tolerance: float = 0.01,
) -> dict[str, float | int | bool | str]:
    """Audit actual cash against opening cash plus recorded cash deltas.

    If no opening balance is supplied or stored as ``opening_cash``,
    ``starting_cash``, or ``initial_cash``, it is reconstructed from actual
    cash.  The audit labels that source as ``inferred`` because such a result
    cannot independently detect an unrecorded historical balance change.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")

    records = getattr(studio, "transactions", ()) or ()
    cash_delta = 0.0
    transaction_count = 0
    for record in records:
        value = _number(_record_value(record, "cash_delta", 0.0), float("nan"))
        if math.isfinite(value):
            cash_delta += value
            transaction_count += 1

    actual_cash = _number(getattr(studio, "cash", 0.0))
    source = "argument"
    if opening_cash is None:
        source = "attribute"
        for name in ("opening_cash", "starting_cash", "initial_cash"):
            if hasattr(studio, name):
                opening_cash = _number(getattr(studio, name))
                break
        else:
            opening_cash = actual_cash - cash_delta
            source = "inferred"
    opening = _number(opening_cash)
    expected_cash = opening + cash_delta
    difference = actual_cash - expected_cash
    return {
        "opening_cash": opening,
        "opening_cash_source": source,
        "recorded_cash_delta": cash_delta,
        "expected_cash": expected_cash,
        "actual_cash": actual_cash,
        "difference": difference,
        "balanced": abs(difference) <= tolerance,
        "transaction_count": transaction_count,
    }


__all__ = [
    "Transaction",
    "TransactionKind",
    "committed_monthly_cost",
    "financing_inflow",
    "forward_runway_months",
    "operating_expense",
    "operating_revenue",
    "principal_payment",
    "reconcile_cash",
    "record_transaction",
]
