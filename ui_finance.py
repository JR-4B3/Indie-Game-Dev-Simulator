"""Finance board for short-term bank debt and next-project publisher deals."""

from __future__ import annotations

import curses

from simulation import LOAN_OFFERS, PUBLISHER_OFFERS, GameState, loan_weekly_obligation
from ui_common import add_text, draw_box, draw_selectable_list, money


def draw_finance_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    studio = state.studio
    draw_box(panel, "Finance Desk | Bank Loans & Publisher Deals")
    tabs = ("Bank loans", "Publisher deals")
    for index, tab in enumerate(tabs):
        label = f"[{tab}]" if state.finance_tab == index else f" {tab} "
        add_text(panel, 1, 2 + index * 20, label, 18, curses.color_pair(3) | curses.A_BOLD if state.finance_tab == index else 0)
    debt = sum(loan.balance for loan in studio.loans)
    add_text(panel, 3, 2, f"Cash {money(studio.cash)} | Debt {money(debt)} | Required loan payments {money(loan_weekly_obligation(studio))}/week", width - 4, curses.A_BOLD)
    if state.finance_tab == 0:
        state.selected_finance_offer = min(state.selected_finance_offer, len(LOAN_OFFERS) - 1)
        rows = []
        for offer in LOAN_OFFERS:
            payment = offer["principal"] * (offer["rate"] / 52) / (1 - (1 + offer["rate"] / 52) ** -offer["weeks"])
            rows.append((f"{offer['name']:<18} {money(offer['principal']):>10} | {offer['rate']:>5.1%} APR | {offer['weeks']:>3}w | about {money(payment)}/week", 0))
        draw_selectable_list(panel, rows, state.selected_finance_offer, True, y=5, width=width - 4, visible=len(rows))
        add_text(panel, 10, 2, "Loans add cash now, then automatically take their payment every week. Missed runway is still dangerous.", width - 4, curses.color_pair(5))
    else:
        state.selected_finance_offer = min(state.selected_finance_offer, len(PUBLISHER_OFFERS) - 1)
        rows = []
        for offer in PUBLISHER_OFFERS:
            selected = studio.pending_publisher == offer["name"]
            marker = "SELECTED " if selected else ""
            rows.append((f"{marker}{offer['name']:<20} advance {money(offer['advance']):>10} | rep {offer['min_rep']:>2} | {offer['recoup_share']:.0%} until recouped, {offer['post_recoup_share']:.0%} after", curses.color_pair(3) if selected else 0))
        draw_selectable_list(panel, rows, state.selected_finance_offer, True, y=5, width=width - 4, visible=len(rows))
        add_text(panel, 10, 2, "Select one deal for the next project. The advance is paid on greenlight and publisher royalties reduce every sale.", width - 4, curses.color_pair(5))
    add_text(panel, height - 2, 2, "Up/Down choose | Left/Right switch desk | Enter accept/select | Backspace return to Hub", width - 4, curses.color_pair(4))
