"""New Game wizard: original/sequel chooser, genre/theme mix, creative\nbrief with market intelligence, and storefront selection."""

from __future__ import annotations

import curses

from game_data import GENRES, GOOD_MATCHES, TOPICS
from simulation import (
    AUDIENCES,
    CHANNELS,
    CREATIVE_DIRECTIONS,
    GAME_FORMATS,
    MARKETING,
    RELEASE_STRATEGIES,
    SCOPES,
    GameState,
    capacity_drains,
    concept_focus,
    market_report,
    monthly_fixed_cost,
    plan_requirements,
    projected_weekly_output,
)
from ui_common import COLOR_GOOD, add_text, draw_box, draw_selectable_list, game_title, meter, money, range_meter, rating_text, update_status


def sequel_choices(state: GameState) -> list:
    return [None] + list(reversed(state.studio.catalog))


def topic_order(state: GameState) -> list[tuple[str, str]]:
    """The 300+ themes, tiered by signal for the currently selected genre.

    Returns ``(topic, tier)`` rows ordered: ``"strong"`` proven audience
    (your buyers, strongest first), then ``"fit"`` good genre fits, then
    everything else (``"rest"``). This keeps promising themes at the top
    instead of making the player scrub an alphabetical wall; ordering is
    presentation-only — ``selected_topic`` remains an index into TOPICS.
    """
    genre = GENRES[state.selected_genre]
    fans = state.studio.topic_fans
    fits = GOOD_MATCHES.get(genre, set())
    strong = sorted((topic for topic in TOPICS if fans.get(topic, 0) > 0), key=lambda topic: -fans[topic])
    good = sorted(topic for topic in TOPICS if fans.get(topic, 0) <= 0 and topic in fits)
    rest = sorted(topic for topic in TOPICS if fans.get(topic, 0) <= 0 and topic not in fits)
    return [(topic, "strong") for topic in strong] + [(topic, "fit") for topic in good] + [(topic, "rest") for topic in rest]


def topic_rows(state: GameState) -> list[tuple[str, int]]:
    """Tiered topics as drawable ``(text, attr)`` rows."""
    return [
        (topic, (curses.color_pair(COLOR_GOOD) | curses.A_BOLD) if tier == "strong" else curses.color_pair(COLOR_GOOD) if tier == "fit" else 0)
        for topic, tier in topic_order(state)
    ]


def topic_position(state: GameState, order: list[tuple[str, int]]) -> int:
    """Position of the currently selected topic inside the tiered order."""
    current = TOPICS[state.selected_topic]
    return next((index for index, (topic, _) in enumerate(order) if topic == current), 0)


def select_topic_at(state: GameState, order: list[tuple[str, int]], position: int) -> None:
    state.selected_topic = TOPICS.index(order[position % len(order)][0])


PLAN_FIELDS = (
    ("Scope", "selected_scope", SCOPES),
    ("Game format", "selected_format", GAME_FORMATS),
    ("Audience", "selected_audience", AUDIENCES),
    ("Lead bet", "selected_creative_primary", CREATIVE_DIRECTIONS),
    ("Support bet", "selected_creative_secondary", CREATIVE_DIRECTIONS),
    ("Launch life", "selected_release_strategy", RELEASE_STRATEGIES),
    ("Marketing", "selected_marketing", MARKETING),
)


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
    plan_height = top_height + storefront_height
    genre = screen.derwin(top_height, genre_width, 2, 0)
    topic = screen.derwin(top_height, theme_width, 2, genre_width + 1)
    plan = screen.derwin(plan_height, plan_width, 2, genre_width + theme_width + 2)
    genre_blend = GENRES[state.selected_secondary_genre]
    theme_blend = TOPICS[state.selected_secondary_topic]
    draw_box(genre, "1 Genre")
    draw_box(topic, "2 Theme")
    draw_box(plan, "3 Creative Brief & Market")
    if genre_blend != GENRES[state.selected_genre]:
        add_text(genre, 0, 11, f"+ {genre_blend}", genre_width - 13, curses.color_pair(3) | curses.A_BOLD)
    if theme_blend != TOPICS[state.selected_topic]:
        add_text(topic, 0, 11, f"+ {theme_blend}", theme_width - 13, curses.color_pair(3) | curses.A_BOLD)
    genre_rows = [(name, curses.color_pair(COLOR_GOOD) if state.studio.genre_fans.get(name, 0) > 0 else 0) for name in GENRES]
    genre_blend_mode = state.mix_blend and state.new_game_step == 0
    if genre_blend_mode:
        genre_rows = [(name, curses.color_pair(3) if index == state.selected_genre else attr) for index, (name, attr) in enumerate(genre_rows)]
        add_text(genre, 1, 2, "BLEND (yellow = primary)", genre_width - 4, curses.color_pair(3) | curses.A_BOLD)
    else:
        add_text(genre, 1, 2, "PRIMARY" + (" (green = fans)" if state.studio.genre_fans else ""), genre_width - 4, curses.A_BOLD)
    genre_visible = max(1, top_height - 3)
    genre_selected = state.selected_secondary_genre if genre_blend_mode else state.selected_genre
    draw_selectable_list(genre, genre_rows, genre_selected, state.new_game_step == 0, y=2, width=genre_width - 4, visible=genre_visible)

    ordered_topics = topic_order(state)
    topic_blend_mode = state.mix_blend and state.new_game_step == 1
    rows = topic_rows(state)
    if topic_blend_mode:
        primary_topic = TOPICS[state.selected_topic]
        rows = [(topic, curses.color_pair(3) if topic == primary_topic else attr) for topic, attr in rows]
        add_text(topic, 1, 2, "BLEND (yellow = primary)", theme_width - 4, curses.color_pair(3) | curses.A_BOLD)
    else:
        add_text(topic, 1, 2, "PRIMARY (green = signal)", theme_width - 4, curses.A_BOLD)
    topic_visible = max(1, top_height - 3)
    current_topic = TOPICS[state.selected_secondary_topic if topic_blend_mode else state.selected_topic]
    topic_selected = next((index for index, (topic_name, _) in enumerate(ordered_topics) if topic_name == current_topic), 0)
    draw_selectable_list(topic, rows, topic_selected, state.new_game_step == 1, y=2, width=theme_width - 4, visible=topic_visible)

    scope = SCOPES[state.selected_scope]
    marketing = MARKETING[state.selected_marketing]
    channel_data = CHANNELS[state.selected_channel]
    audience = AUDIENCES[state.selected_audience]
    game_format = GAME_FORMATS[state.selected_format]
    primary_direction = CREATIVE_DIRECTIONS[state.selected_creative_primary]
    secondary_direction = CREATIVE_DIRECTIONS[state.selected_creative_secondary]
    release_strategy = RELEASE_STRATEGIES[state.selected_release_strategy]
    report = market_report(state)
    inner = plan_width - 4
    meter_width = max(8, min(18, plan_width - 40))
    title_mode = "TYPE NAME, ENTER TO ACCEPT" if state.naming_game else "E edit / R randomize"
    add_text(plan, 1, 2, f"Title      {state.draft_title}_  [{title_mode}]" if state.naming_game else f"Title      {state.draft_title}  [{title_mode}]", inner, curses.color_pair(3) | curses.A_BOLD)

    add_text(plan, 3, 2, "PLAN", inner, curses.A_BOLD)
    field_specs = [
        ("Scope", scope["name"], f"base {scope['work']:,} work | {money(scope['setup'])}"),
        ("Game format", game_format["name"], f"+{game_format['work'] - 1:.0%} work | {money(game_format['setup'])} tech"),
        ("Audience", audience["name"], ""),
        ("Lead bet", primary_direction["name"], ""),
        ("Support bet", secondary_direction["name"], ""),
        ("Launch life", release_strategy["name"], release_strategy["tradeoff"]),
        ("Marketing", marketing["name"], f"{money(marketing['cost'])} | hype {5 + marketing['boost'] / 25:.0f}"),
    ]
    rows = []
    for index, (label, value, detail) in enumerate(field_specs):
        shown = f"<{value}>" if state.new_game_step == 2 and index == state.selected_focus else value
        rows.append((f"{label:<11} {shown}" + (f" | {detail}" if detail else ""), 0))
    draw_selectable_list(plan, rows, state.selected_focus, state.new_game_step == 2, y=4, width=inner, scroll=False)
    if state.new_game_step == 2:
        _, attribute, options = PLAN_FIELDS[state.selected_focus]
        current = getattr(state, attribute)
        add_text(plan, 11, 2, "Options", inner, curses.A_BOLD)
        chip_x = 11
        for index, option in enumerate(options):
            chip = option["name"]
            if chip_x + len(chip) > plan_width - 2:
                break
            add_text(plan, 11, chip_x, chip, len(chip), curses.color_pair(3) | curses.A_BOLD if index == current else curses.color_pair(2))
            chip_x += len(chip) + 2
    else:
        add_text(plan, 11, 2, f"Trade-off   {primary_direction['tradeoff']} + {secondary_direction['tradeoff']}", inner, curses.color_pair(2))

    fit_attr = curses.color_pair(COLOR_GOOD) if report["score_low"] >= 52 else curses.color_pair(5) if report["score_high"] < 38 else 0
    cost = scope["setup"] + game_format["setup"] + release_strategy["setup"] + marketing["cost"] + channel_data["fee"]
    output = projected_weekly_output(state.studio, concept_focus(state))
    week_low = max(4, round(report["work_low"] / output))
    week_high = max(week_low, round(report["work_high"] / output))
    runway_weeks = max(0, state.studio.cash - cost) / max(1, monthly_fixed_cost(state.studio)) * 4.33
    runway_danger = runway_weeks < week_high
    week_scale = max(runway_weeks, week_high)
    drains = capacity_drains(state.studio)
    drain_text = " | ".join(drains) if drains else "full capacity"
    requirements = plan_requirements(state)
    if requirements:
        readiness = f"LOCKED: needs {', '.join(requirements)}"
    elif runway_danger:
        readiness = f"HIGH FAILURE RISK: {runway_weeks:.0f}w runway vs forecast up to {week_high}w"
    else:
        readiness = "PRODUCTION READY - forecast still carries uncertainty"
    readiness_attr = curses.color_pair(5) if requirements or runway_danger else curses.color_pair(4) | curses.A_BOLD
    genre_name = GENRES[state.selected_genre]
    genre_mix = genre_name if genre_name == GENRES[state.selected_secondary_genre] else f"{genre_name}/{GENRES[state.selected_secondary_genre]}"
    topic_name = TOPICS[state.selected_topic]
    topic_mix = topic_name if topic_name == TOPICS[state.selected_secondary_topic] else f"{topic_name} + {TOPICS[state.selected_secondary_topic]}"
    sequel = next((game for game in state.studio.catalog if game.game_id == state.sequel_game_id), None)

    if plan_height < 28:
        add_text(plan, 13, 2, f"MARKET Fit {report['score_low']}-{report['score_high']} | confidence {report['confidence']}%", inner, fit_attr | curses.A_BOLD)
        add_text(plan, 14, 2, f"Interest {report['audience_low']:,}-{report['audience_high']:,} | {report['outlook']}", inner, fit_attr)
        add_text(plan, 15, 2, f"WORKLOAD {report['work_low']:,}-{report['work_high']:,} | {week_low}-{week_high}w | ~{output:.0f}/wk", inner, curses.A_BOLD)
        add_text(plan, 16, 2, f"Runway {runway_weeks:.0f}w | need {week_high}w | cash {money(cost)}", inner, curses.color_pair(5) if runway_danger else 0)
        add_text(plan, 17, 2, readiness, inner, readiness_attr)
        add_text(plan, 18, 2, f"BRIEF {scope['name']} {game_format['name']} {genre_mix} | {topic_mix}", inner, curses.A_BOLD)
    else:
        add_text(plan, 13, 2, "MARKET", inner, curses.A_BOLD)
        add_text(plan, 14, 2, f"Fit        {range_meter(report['score_low'], report['score_high'], 100, meter_width)} {report['score_low']}-{report['score_high']}", inner, fit_attr)
        add_text(plan, 15, 2, f"Interest   {report['audience_low']:,}-{report['audience_high']:,} players", inner)
        add_text(plan, 16, 2, f"Confidence {meter(report['confidence'], 100, meter_width)} {report['confidence']}%", inner)
        add_text(plan, 17, 2, f"Rivals     {report['competitors_low']}-{report['competitors_high']} | risk {report['risk']} | research {report['research']}", inner)
        add_text(plan, 18, 2, f"Outlook    {report['outlook']}", inner, fit_attr)
        add_text(plan, 20, 2, "WORKLOAD", inner, curses.A_BOLD)
        add_text(plan, 21, 2, f"Forecast   {report['work_low']:,}-{report['work_high']:,} work ≈ {week_low}-{week_high}w", inner)
        add_text(plan, 22, 2, f"Runway     {meter(runway_weeks, week_scale, meter_width)} {runway_weeks:.0f}w", inner, curses.color_pair(5) if runway_danger else 0)
        add_text(plan, 23, 2, f"Needed     {meter(week_high, week_scale, meter_width)} {week_high}w", inner)
        add_text(plan, 24, 2, f"Capacity   ~{output:.0f}/wk | drains {drain_text}", inner, curses.color_pair(5) if drains else 0)
        add_text(plan, 25, 2, f"Cash due   {money(cost)} | {(state.studio.cash - cost) / max(1, monthly_fixed_cost(state.studio)):.1f} mo after setup", inner)
        add_text(plan, 27, 2, readiness, inner, readiness_attr)
        if plan_height < 35:
            add_text(plan, 29, 2, "BRIEF", inner, curses.A_BOLD)
            add_text(plan, 30, 2, f"{scope['name']} {game_format['name']} {genre_mix} | {topic_mix} | {audience['name']}", inner)
        else:
            add_text(plan, 29, 2, "BRIEF", inner, curses.A_BOLD)
            add_text(plan, 30, 2, f"{scope['name']} {game_format['name']} {genre_mix} game about {topic_mix}", inner)
            add_text(plan, 31, 2, f"for {audience['name']}; lead {primary_direction['name']}, support {secondary_direction['name']};", inner)
            add_text(plan, 32, 2, f"{release_strategy['name']} launch, {marketing['name']} marketing, on {channel_data['name']}.", inner)
            if sequel:
                score = "score n/a" if sequel.release_date == "Historical" else f"{sequel.score}/100"
                add_text(plan, 33, 2, f"Sequel to {sequel.title} ({score})", inner, curses.color_pair(2))

    storefront_width = genre_width + theme_width + 1
    storefront = screen.derwin(storefront_height, storefront_width, 2 + top_height, 0)
    draw_box(storefront, "4 Market & Store")
    store_width = max(8, storefront_width - 24)
    add_text(storefront, 1, 2, f"  {'STORE':<{store_width}} | {'CUT':>4} | {'COST':>8}", storefront_width - 4, curses.A_BOLD)
    visible = storefront_height - 3
    channel_rows = [(f"{channel['name']:<{store_width}} | {channel['cut']:>4.0%} | {money(channel['fee']):>8}", 0) for channel in CHANNELS]
    draw_selectable_list(storefront, channel_rows, state.selected_channel, state.new_game_step == 3, y=2, width=storefront_width - 4, visible=visible)
