"""Contract Board page: monthly client offers on the left, contractor\nprofile, active contract, and queue on the right."""

from __future__ import annotations

import curses

from simulation import GameState, contract_offer_eta_weeks, estimated_contract_weeks
from ui_common import add_text, draw_box, draw_selectable_list, money


def contract_board_width(width: int) -> int:
    """Width of the offers board; shared with the mouse handler."""
    return max(46, width * 2 // 3)


def draw_contract_screen(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel_height = height - 4
    board_width = contract_board_width(width)
    detail_width = width - board_width - 1
    board = screen.derwin(panel_height, board_width, 2, 0)
    detail = screen.derwin(panel_height, detail_width, 2, board_width + 1)
    studio = state.studio
    auto = "ON" if studio.auto_contracts else "OFF"
    draw_box(board, f"Contract Board | {len(studio.contract_offers)} offers | Auto {auto}")
    draw_box(detail, "Contract Queue & Profile")
    if not studio.contract_offers:
        add_text(board, 1, 2, "No contract offers. The board refreshes monthly.", board_width - 4)
    eligible = [index for index, offer in enumerate(studio.contract_offers) if offer.reputation_required <= studio.contractor_reputation]
    if state.selected_contract not in eligible:
        state.selected_contract = eligible[0] if eligible else -1
    board_inner = board_width - 4
    board_expanded = board_inner >= 85
    client_width = 18 if board_expanded else 10
    focus_width = 10 if board_expanded else 5
    job_width = max(8, board_inner - (69 if board_expanded else 32))
    if board_expanded:
        board_header = f"  {'CLIENT':<{client_width}} {'CONTRACT':<{job_width}} {'FOCUS':<{focus_width}} {'LEVEL':>5} {'PAYOUT':>10} {'ETA':>5} {'DUE':>5} {'REQ REP':>7}"
    else:
        board_header = f"  {'CLIENT':<{client_width}} {'CONTRACT':<{job_width}} {'FOCUS':<{focus_width}} {'PAY':>8} {'DUE':>4}"
    add_text(board, 1, 2, board_header, board_inner, curses.A_BOLD)
    offer_rows = []
    for contract in studio.contract_offers[: panel_height - 3]:
        estimate = contract_offer_eta_weeks(contract)
        locked = studio.contractor_reputation < contract.reputation_required
        if board_expanded:
            text = f"{contract.client[:client_width]:<{client_width}} {contract.title[:job_width]:<{job_width}} {contract.focus[:focus_width]:<{focus_width}} {contract.difficulty:>5} {money(contract.payout):>10} {estimate:>4}w {contract.weeks_left:>4}w {contract.reputation_required:>7}"
        else:
            text = f"{contract.client[:client_width]:<{client_width}} {contract.title[:job_width]:<{job_width}} {contract.focus[:focus_width]:<{focus_width}} {money(contract.payout):>8} {contract.weeks_left:>3}w"
        offer_rows.append((text, curses.color_pair(5) if locked else 0))
    draw_selectable_list(board, offer_rows, state.selected_contract, True, y=2, width=board_width - 4, scroll=False, highlight_wins=False)

    add_text(detail, 1, 2, f"Contractor reputation  {studio.contractor_reputation:.1f}/100", detail_width - 4, curses.A_BOLD)
    add_text(detail, 2, 2, f"Completed {studio.contracts_completed} | Failed {studio.contracts_failed}", detail_width - 4)
    add_text(detail, 3, 2, f"Auto accept: {auto}", detail_width - 4, curses.color_pair(4) if studio.auto_contracts else curses.color_pair(5))
    active = studio.contract
    if active:
        progress = 0 if active.required_work <= 0 else active.work_done / active.required_work
        estimate = estimated_contract_weeks(studio, active)
        source = "AUTO" if active.auto_accepted else "MANUAL"
        add_text(detail, 5, 2, f"ACTIVE {source} CONTRACT", detail_width - 4, curses.color_pair(3) | curses.A_BOLD)
        add_text(detail, 6, 2, f"{active.client}", detail_width - 4)
        add_text(detail, 7, 2, active.title, detail_width - 4)
        add_text(detail, 8, 2, f"Focus {active.focus} | D{active.difficulty}", detail_width - 4)
        add_text(detail, 9, 2, f"Progress {progress:.0%} | est {estimate}w", detail_width - 4)
        add_text(detail, 10, 2, f"Deadline {active.weeks_left}w | {money(active.payout)}", detail_width - 4)
    else:
        add_text(detail, 5, 2, "No active contract", detail_width - 4)
    queue_row = 12
    if queue_row < panel_height - 1:
        add_text(detail, queue_row, 2, f"QUEUE ({len(studio.contract_queue)})", detail_width - 4, curses.A_BOLD)
        for row, contract in enumerate(studio.contract_queue[: panel_height - queue_row - 2], queue_row + 1):
            source = "A" if contract.auto_accepted else "M"
            add_text(detail, row, 2, f"{row - queue_row}. [{source}] {contract.focus}: {contract.title} ({money(contract.payout)})", detail_width - 4)
