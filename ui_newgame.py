"""New Game wizard: original/sequel chooser, genre/theme mix, creative\nbrief with market intelligence, and storefront selection."""

from __future__ import annotations

import curses

from game_data import GENRES, TOPICS
from simulation import (
    AUDIENCES,
    CHANNELS,
    CREATIVE_DIRECTIONS,
    GAME_FORMATS,
    MARKETING,
    RELEASE_STRATEGIES,
    SCOPES,
    GameState,
    concept_focus,
    market_report,
    monthly_fixed_cost,
    plan_requirements,
    projected_weekly_output,
)
from ui_common import add_text, draw_box, draw_selectable_list, game_title, money, rating_text, update_status


def sequel_choices(state: GameState) -> list:
    return [None] + list(reversed(state.studio.catalog))


def draw_project_type(screen: curses.window, state: GameState, width: int, height: int) -> None:
    panel = screen.derwin(height - 4, width, 2, 0)
    draw_box(panel, "Start Production | Original Game or Sequel")
    add_text(panel, 1, 2, "Choose an original concept or continue one of your released games.", width - 4, curses.color_pair(4))
    choices = sequel_choices(state)
    state.selected_sequel_choice = min(state.selected_sequel_choice, len(choices) - 1)
    rows = []
    for choice in choices:
        if choice is None:
            text = "ORIGINAL GAME  Create a new genre/theme concept and generated title"
        else:
            label = game_title(choice, 34)
            text = f"SEQUEL         {label:<34} {choice.genre[:13]:<13} rating {rating_text(choice):>3} | hype {choice.hype:.0f} | {choice.monthly_players:,} monthly players | {update_status(choice)}"
        rows.append((text, 0))
    draw_selectable_list(panel, rows, state.selected_sequel_choice, True, y=3, width=width - 4, visible=height - 8)
    tracked = len(state.studio.catalog)
    missing = max(0, state.studio.released_games - tracked)
    if missing:
        add_text(panel, height - 3, 2, f"{missing} older release(s) lack recoverable title data and cannot be selected as sequels.", width - 4, curses.color_pair(5))
    add_text(panel, height - 2, 2, "Enter or double-click to continue. Mouse wheel scrolls the release list.", width - 4, curses.color_pair(4))


def new_game_panel_geometry(width: int, height: int) -> tuple[int, int, int, int, int]:
    storefront_height = 11
    top_height = max(9, height - 4 - storefront_height)
    genre_width = max(16, min(28, width // 6))
    theme_width = max(18, min(32, width // 5))
    plan_width = width - genre_width - theme_width - 2
    return top_height, genre_width, theme_width, plan_width, storefront_height


def draw_new_game(screen: curses.window, state: GameState, width: int, height: int) -> None:
    if state.new_game_step == -1:
        draw_project_type(screen, state, width, height)
        return
    top_height, genre_width, theme_width, plan_width, storefront_height = new_game_panel_geometry(width, height)
    genre = screen.derwin(top_height, genre_width, 2, 0)
    topic = screen.derwin(top_height, theme_width, 2, genre_width + 1)
    plan = screen.derwin(top_height + storefront_height, plan_width, 2, genre_width + theme_width + 2)
    draw_box(genre, "1 Genre Mix")
    draw_box(topic, "2 Theme Mix")
    draw_box(plan, "3 Creative Brief & Market")
    add_text(genre, 1, 2, "PRIMARY", genre_width - 4, curses.A_BOLD)
    genre_visible = max(1, top_height - 5)
    draw_selectable_list(genre, [(name, 0) for name in GENRES], state.selected_genre, state.new_game_step == 0, y=2, width=genre_width - 4, visible=genre_visible)
    genre_blend = GENRES[state.selected_secondary_genre]
    add_text(genre, top_height - 2, 2, f"Blend < {genre_blend} >", genre_width - 4, curses.color_pair(4) if state.new_game_step == 0 else 0)

    add_text(topic, 1, 2, "PRIMARY", theme_width - 4, curses.A_BOLD)
    topic_visible = max(1, top_height - 5)
    draw_selectable_list(topic, [(name, 0) for name in TOPICS], state.selected_topic, state.new_game_step == 1, y=2, width=theme_width - 4, visible=topic_visible)
    theme_blend = TOPICS[state.selected_secondary_topic]
    add_text(topic, top_height - 2, 2, f"Blend < {theme_blend} >", theme_width - 4, curses.color_pair(4) if state.new_game_step == 1 else 0)

    scope = SCOPES[state.selected_scope]
    marketing = MARKETING[state.selected_marketing]
    channel_data = CHANNELS[state.selected_channel]
    audience = AUDIENCES[state.selected_audience]
    game_format = GAME_FORMATS[state.selected_format]
    primary_direction = CREATIVE_DIRECTIONS[state.selected_creative_primary]
    secondary_direction = CREATIVE_DIRECTIONS[state.selected_creative_secondary]
    release_strategy = RELEASE_STRATEGIES[state.selected_release_strategy]
    report = market_report(state)
    title_mode = "TYPE NAME, ENTER TO ACCEPT" if state.naming_game else "E edit / R randomize"
    add_text(plan, 1, 2, f"Title      {state.draft_title}_  [{title_mode}]" if state.naming_game else f"Title      {state.draft_title}  [{title_mode}]", plan_width - 4, curses.color_pair(3) | curses.A_BOLD)
    fields = [
        f"Scope       {scope['name']} | base {scope['work']:,} work | {money(scope['setup'])}",
        f"Game format {game_format['name']} | +{game_format['work'] - 1:.0%} work | {money(game_format['setup'])} tech",
        f"Audience    {audience['name']}",
        f"Lead bet    {primary_direction['name']}",
        f"Support bet {secondary_direction['name']}",
        f"Launch life {release_strategy['name']} | {release_strategy['tradeoff']}",
        f"Marketing   {marketing['name']} | {money(marketing['cost'])} | hype {5 + marketing['boost'] / 25:.0f}",
    ]
    draw_selectable_list(plan, [(text, 0) for text in fields], state.selected_focus, state.new_game_step == 2, y=2, width=plan_width - 4, scroll=False)
    cost = scope["setup"] + game_format["setup"] + release_strategy["setup"] + marketing["cost"] + channel_data["fee"]
    output = projected_weekly_output(state.studio, concept_focus(state))
    week_low = max(4, round(report["work_low"] / output))
    week_high = max(week_low, round(report["work_high"] / output))
    add_text(plan, 10, 2, "MARKET INTELLIGENCE", plan_width - 4, curses.A_BOLD)
    add_text(plan, 11, 2, f"{report['outlook']} | Research confidence {report['confidence']}% (team Research {report['research']})", plan_width - 4, curses.color_pair(4) if report["score_low"] >= 52 else curses.color_pair(5) if report["score_high"] < 38 else 0)
    add_text(plan, 12, 2, f"Fit likely {report['score_low']}-{report['score_high']}/100 | Interested players {report['audience_low']:,}-{report['audience_high']:,}", plan_width - 4)
    add_text(plan, 13, 2, f"Competing releases {report['competitors_low']}-{report['competitors_high']} | Risk exposure {report['risk']} | rivals share audience overlap", plan_width - 4)
    add_text(plan, 14, 2, f"Workload forecast {report['work_low']:,}-{report['work_high']:,} work | roughly {week_low}-{week_high} weeks", plan_width - 4)
    add_text(plan, 15, 2, f"TRADE-OFF  {primary_direction['tradeoff']} + {secondary_direction['tradeoff']}", plan_width - 4)
    requirements = plan_requirements(state)
    runway_weeks = max(0, state.studio.cash - cost) / max(1, monthly_fixed_cost(state.studio)) * 4.33
    runway_danger = runway_weeks < week_high
    if requirements:
        readiness = f"LOCKED: needs {', '.join(requirements)}"
    elif runway_danger:
        readiness = f"HIGH FAILURE RISK: {runway_weeks:.0f}w runway vs forecast up to {week_high}w"
    else:
        readiness = "PRODUCTION READY - forecast still carries uncertainty"
    add_text(plan, 17, 2, readiness, plan_width - 4, curses.color_pair(5) if requirements or runway_danger else curses.color_pair(4) | curses.A_BOLD)
    summary = f"Cash due {money(cost)} | runway after setup {(state.studio.cash - cost) / max(1, monthly_fixed_cost(state.studio)):.1f} months | estimates can be wrong"
    sequel = next((game for game in state.studio.catalog if game.game_id == state.sequel_game_id), None)
    if sequel:
        score = "score n/a" if sequel.release_date == "Historical" else f"{sequel.score}/100"
        summary += f" | sequel to {sequel.title} ({score})"
    add_text(plan, 18, 2, summary, plan_width - 4, curses.color_pair(4) if not requirements and not runway_danger else curses.color_pair(5))

    storefront_width = genre_width + theme_width + 1
    storefront = screen.derwin(storefront_height, storefront_width, 2 + top_height, 0)
    draw_box(storefront, "4 Market & Store")
    store_width = max(8, storefront_width - 24)
    add_text(storefront, 1, 2, f"  {'STORE':<{store_width}} | {'CUT':>4} | {'COST':>8}", storefront_width - 4, curses.A_BOLD)
    visible = storefront_height - 3
    channel_rows = [(f"{channel['name']:<{store_width}} | {channel['cut']:>4.0%} | {money(channel['fee']):>8}", 0) for channel in CHANNELS]
    draw_selectable_list(storefront, channel_rows, state.selected_channel, state.new_game_step == 3, y=2, width=storefront_width - 4, visible=visible)
