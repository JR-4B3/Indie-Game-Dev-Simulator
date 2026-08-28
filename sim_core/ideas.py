"""Rough idea generation: the front end of the development pipeline.

The studio no longer assembles a game from a genre/theme wizard. Instead
rested team members produce rough pitches over time. A rough idea carries a
player fantasy, a main activity, a setting and possibly one unusual hook.
Genre and theme are inferred internally (so the existing market simulation
keeps working) but the player never selects them.

This module is deliberately independent from the main simulation: it works
on duck-typed studios and employees, mirroring ``sim_core/market.py``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from game_data import GENRES, TOPICS


def _validate(name: str, table: tuple[str, ...], source: str) -> str:
    if name not in table:
        raise ValueError(f"ideas.py references unknown {source}: {name!r}")
    return name


# ---------------------------------------------------------------------------
# Authored component tables. Every genre/topic reference is validated against
# game_data at import so a typo fails loudly instead of corrupting inference.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Fantasy:
    text: str
    genre_hint: str = ""


FANTASIES: tuple[Fantasy, ...] = (
    Fantasy("become a legend on your own terms"),
    Fantasy("outsmart a world built to fool you"),
    Fantasy("care for something fragile until it thrives"),
    Fantasy("survive what should have ended you"),
    Fantasy("build an empire from almost nothing"),
    Fantasy("master a deep system completely"),
    Fantasy("get lost in a beautiful unknown"),
    Fantasy("feel unbeatable, briefly and earned"),
    Fantasy("uncover a truth someone buried"),
    Fantasy("compete and prove you are the best"),
    Fantasy("escape a life that never fit"),
    Fantasy("make a mess and be the one to fix it"),
)


@dataclass(frozen=True)
class Activity:
    name: str
    genre: str
    secondary_genre: str
    tags: frozenset[str]


ACTIVITIES: tuple[Activity, ...] = (
    Activity("guide a drifting settlement through hostile lands", "Simulation", "Strategy", frozenset({"management", "exploration", "systems"})),
    Activity("build and automate a growing machine network", "Automation", "Building Game", frozenset({"creation", "systems"})),
    Activity("delve ever deeper into shifting ruins", "Roguelite", "Action", frozenset({"exploration", "reflex", "chance"})),
    Activity("solve the town's mysteries through conversation", "Adventure", "Visual Novel", frozenset({"narrative", "exploration"})),
    Activity("defend the last bastion against endless waves", "Strategy", "Action", frozenset({"systems", "reflex"})),
    Activity("race improvised machines down impossible tracks", "Racing", "Skill Game", frozenset({"reflex", "competition"})),
    Activity("run a small business in a strange city", "Economic Simulation", "Simulation", frozenset({"management", "systems"})),
    Activity("cultivate a quiet farm on the edge of nowhere", "Cozy Game", "Simulation", frozenset({"creation", "management"})),
    Activity("duel rivals in fast, precise combat", "Fighting Game", "Action", frozenset({"reflex", "competition"})),
    Activity("survive a collapsing expedition into the wild", "Survival Game", "Roguelike", frozenset({"exploration", "chance", "systems"})),
    Activity("command armies across a living map", "Real-Time Strategy", "Strategy", frozenset({"systems", "management", "competition"})),
    Activity("explore a handcrafted world and chart its secrets", "Metroidvania", "Adventure", frozenset({"exploration", "reflex"})),
    Activity("outwit the table in card duels", "Deckbuilder", "Roguelite", frozenset({"systems", "chance"})),
    Activity("keep fragile creatures alive against the odds", "Simulation", "Puzzle Game", frozenset({"management", "systems"})),
    Activity("parkour across a vertical city", "Platformer", "Action", frozenset({"reflex"})),
    Activity("hunt monsters across vast hunting grounds", "Role-Playing Game", "Action", frozenset({"reflex", "exploration"})),
    Activity("unravel a conspiracy in a rain-soaked capital", "Adventure", "Interactive Movie", frozenset({"narrative"})),
    Activity("pilot a mech through escalating wars", "Action", "Third-Person Shooter", frozenset({"reflex", "systems"})),
    Activity("restore a ruined garden to life", "Cozy Game", "Puzzle Game", frozenset({"creation"})),
    Activity("climb an impossible tower that hates you", "Platformer", "Skill Game", frozenset({"reflex", "chance"})),
    Activity("direct a crew through scripted heists", "Immersive Sim", "Strategy", frozenset({"systems", "narrative"})),
    Activity("run a kitchen that is always one order from chaos", "Simulation", "Economic Simulation", frozenset({"management", "reflex"})),
)


@dataclass(frozen=True)
class Setting:
    name: str
    topics: tuple[str, ...]
    tags: frozenset[str]


SETTINGS: tuple[Setting, ...] = (
    Setting("a flooded machine-city", ("Oceans", "Machines"), frozenset({"atmosphere"})),
    Setting("a cozy mountain village", ("Villages", "Nature"), frozenset({"gentle"})),
    Setting("a derelict space station", ("Space Stations", "Space"), frozenset({"atmosphere", "tech"})),
    Setting("a neon megacity", ("Cyberpunk", "Cities"), frozenset({"atmosphere", "tech"})),
    Setting("an underground kingdom of miners", ("Mining", "Dwarfs"), frozenset({"systems"})),
    Setting("an archipelago of floating islands", ("Islands", "Oceans"), frozenset({"atmosphere"})),
    Setting("a haunted Victorian manor", ("Victorian Age", "Ghosts"), frozenset({"narrative"})),
    Setting("the dying frontier of the wild west", ("Wild West", "Cowboys"), frozenset({"narrative"})),
    Setting("a biopunk jungle research outpost", ("Jungle", "Science"), frozenset({"tech", "atmosphere"})),
    Setting("a monastery of obsessive archivists", ("Books", "Religion"), frozenset({"narrative"})),
    Setting("a highway through the end of the world", ("Apocalypse", "Survivalism"), frozenset({"atmosphere"})),
    Setting("the courts of scheming noble houses", ("Noble Houses", "Politics"), frozenset({"narrative", "systems"})),
    Setting("a busy spaceport at the galaxy's edge", ("Space", "Aliens"), frozenset({"systems", "tech"})),
    Setting("a sunken kingdom", ("Atlantis", "Oceans"), frozenset({"atmosphere"})),
    Setting("a clockwork metropolis", ("Steampunk", "Machines"), frozenset({"systems", "tech"})),
    Setting("the backroads of a fantasy empire", ("Fantasy", "Magic"), frozenset({"narrative"})),
    Setting("a rain-slick port town with secrets", ("Crime", "Detective"), frozenset({"narrative"})),
    Setting("an ancient tomb city", ("Ancient Egypt", "Mummies"), frozenset({"atmosphere"})),
    Setting("a frozen frontier station", ("Astronauts", "Science"), frozenset({"tech", "atmosphere"})),
    Setting("a carnival that arrives without warning", ("Circus", "Comedy"), frozenset({"gentle"})),
)


@dataclass(frozen=True)
class Hook:
    name: str
    uncertainty: str
    tags: frozenset[str]
    doubt: float


HOOKS: tuple[Hook, ...] = (
    Hook("the world rearranges itself every night", "What keeps a rearranging world surprising?", frozenset({"procedural"}), 0.35),
    Hook("every failure permanently scars the town", "How harsh should permanent consequences feel?", frozenset({"persistent", "narrative"}), 0.20),
    Hook("you play the villain's overworked accountant", "Can ledger comedy carry a whole game?", frozenset({"narrative"}), 0.15),
    Hook("the interface lies to you", "How much deception can players enjoy?", frozenset({"systems"}), 0.30),
    Hook("two players share one body", "Does shared control stay fun after an hour?", frozenset({"multiplayer"}), 0.50),
    Hook("time only moves when you move", "Does stopped-time pacing suit every encounter?", frozenset({"systems"}), 0.25),
    Hook("the game remembers previous saves", "Can cross-save memory stay fair?", frozenset({"persistent", "systems"}), 0.35),
    Hook("you must rebuild the town you destroyed in the intro", "Does reversal land emotionally?", frozenset({"narrative"}), 0.10),
    Hook("everyone lies, and the lies are mechanics", "Can social deception work without other people?", frozenset({"social", "narrative"}), 0.40),
    Hook("the soundtrack is built from your actions", "Does generative audio stay musical?", frozenset({"audio"}), 0.40),
    Hook("gravity slowly rotates", "Does rotating gravity stay readable?", frozenset({"reflex"}), 0.45),
    Hook("you inherit failed expeditions from other players", "Do inherited worlds feel fair?", frozenset({"procedural", "persistent"}), 0.55),
)

# Hook tags that push technical doubt up regardless of the team's code skill.
_TECHY_HOOK_TAGS = frozenset({"procedural", "multiplayer", "persistent", "audio"})

# Idea tags used for presentation packages and experiment relevance.
IDEA_TAGS = frozenset(
    {
        "management", "exploration", "systems", "creation", "reflex",
        "competition", "narrative", "chance", "social", "atmosphere",
        "gentle", "tech",
    }
)


_TITLE_HEADS = (
    "Tide", "Ember", "Hollow", "Static", "Lantern", "Rust", "Verdant", "Glass",
    "Iron", "Fable", "Drift", "Cinder", "Moss", "Signal", "Orbit", "Bramble",
    "Slate", "Neon", "Anchor", "Comet", "Marrow", "Flux", "Pale", "Umbra",
)
_TITLE_TAILS = (
    "fall", "bound", "line", "song", "works", "gate", "reach", "forge",
    "hearth", "circuit", "vale", "root", "light", "drift", "tide", "spark",
    "hollow", "veil", "coast", "gardens", "engine", "letters", "harbor", "trail",
)


def _idea_title(rng: random.Random) -> str:
    head = rng.choice(_TITLE_HEADS)
    tail = rng.choice(_TITLE_TAILS)
    if head[-1].lower() == tail[0].lower():
        tail = rng.choice(_TITLE_TAILS)
    style = rng.random()
    if style < 0.45:
        return f"{head}{tail}"
    if style < 0.75:
        return f"{head} {tail.capitalize()}"
    return f"The {head} {tail.capitalize()}"


# ---------------------------------------------------------------------------
# Rough idea model
# ---------------------------------------------------------------------------


@dataclass
class RoughIdea:
    """A raw pitch. Not a game design — a starting point that may die."""

    idea_id: int
    title: str
    fantasy: str
    activity: str
    setting: str
    hook: str
    uncertainty: str
    source: str
    origin: str  # "team" | "release" | "contract" | "training"
    genre: str
    secondary_genre: str
    topic: str
    secondary_topic: str
    clarity: float  # 0..1 internal; shown only as words
    originality: float
    technical_doubt: float
    trend_pull: float  # 0..1, high = rides a trend, cools fast
    created_week: int
    cool_at_week: int
    status: str = "fresh"  # fresh | cooling | dormant
    inspiration_game_id: int | None = None
    franchise_id: int | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def age_weeks(self) -> int:
        return max(0, self.cool_at_week - self.created_week)

    def pitch_lines(self) -> list[str]:
        lines = []
        activity_line = f"You {self.activity} in {self.setting}."
        lines.append(activity_line[0].upper() + activity_line[1:])
        if self.hook:
            lines.append(f"But {self.hook}.")
        return lines

    def signal_words(self) -> list[str]:
        """Short prose descriptors. Never a numeric idea score."""
        words: list[str] = []
        if self.clarity >= 0.75:
            words.append("clear fantasy")
        elif self.clarity >= 0.45:
            words.append("interesting but vague")
        else:
            words.append("incoherent pitch")
        if self.originality >= 0.8:
            words.append("striking concept")
        elif self.originality <= 0.3:
            words.append("familiar territory")
        if self.technical_doubt >= 0.6:
            words.append("technically doubtful")
        elif self.technical_doubt <= 0.25:
            words.append("proven tech")
        if self.hook:
            words.append("unusual hook")
        if self.status == "cooling":
            words.append("cooling")
        elif self.status == "dormant":
            words.append("dormant")
        return words


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def _trait_bias(trait: str) -> dict[str, float]:
    return {
        "Visionary": {"originality": 0.14, "clarity": -0.04},
        "Pragmatic": {"originality": -0.05, "clarity": 0.06},
        "Perfectionist": {"originality": 0.02, "clarity": 0.08},
        "Showman": {"originality": 0.08, "clarity": 0.02},
        "Workaholic": {"originality": 0.0, "clarity": 0.0},
        "Generalist": {"originality": 0.03, "clarity": 0.03},
        "Lone Genius": {"originality": 0.10, "clarity": -0.06},
        "Mentor": {"originality": -0.02, "clarity": 0.10},
    }.get(trait, {"originality": 0.0, "clarity": 0.0})


def _quirk_bias(quirk: str) -> dict[str, float]:
    return {
        "Cautious": {"originality": -0.06, "doubt": -0.05},
        "Burning Passion": {"originality": 0.10},
        "Night Owl": {"originality": 0.04, "clarity": -0.03},
        "Perfectionist Eye": {"originality": 0.0, "clarity": 0.05},
        "Team Player": {"originality": -0.02, "clarity": 0.04},
        "Contrarian": {"originality": 0.12, "clarity": -0.05},
    }.get(quirk, {"originality": 0.0, "clarity": 0.0})


def _dominant_skill(employee) -> str:
    skills = {
        "design": employee.design,
        "art": employee.art,
        "audio": employee.audio,
        "code": employee.code,
        "research": employee.research,
    }
    return max(skills, key=skills.get)


def _pick_components(rng: random.Random, employee) -> tuple:
    """Choose components biased by whoever is pitching."""
    dominant = _dominant_skill(employee)
    if dominant == "design":
        activity = rng.choice([a for a in ACTIVITIES if {"systems", "management"} & a.tags] or ACTIVITIES)
    elif dominant == "art":
        activity = rng.choice([a for a in ACTIVITIES if {"exploration", "creation"} & a.tags] or ACTIVITIES)
    elif dominant == "code":
        activity = rng.choice([a for a in ACTIVITIES if {"systems", "reflex"} & a.tags] or ACTIVITIES)
    elif dominant == "audio":
        activity = rng.choice([a for a in ACTIVITIES if "atmosphere" in {t for s in SETTINGS for t in s.tags}] or ACTIVITIES)
    else:
        activity = rng.choice(ACTIVITIES)
    if dominant in ("art", "audio"):
        setting = rng.choice([s for s in SETTINGS if "atmosphere" in s.tags] or SETTINGS)
    elif dominant == "research":
        setting = rng.choice(SETTINGS)
    else:
        setting = rng.choice(SETTINGS)
    fantasy = rng.choice(FANTASIES)
    # Research-driven pitches chase what is current: higher trend pull, faster cooling.
    trend_pull = 0.30 + employee.research / 260 + rng.uniform(-0.1, 0.15)
    hook_chance = 0.30 + employee.design / 400 + employee.code / 500
    hook = rng.choice(HOOKS) if rng.random() < min(0.6, hook_chance) else None
    return activity, setting, fantasy, hook, max(0.0, min(1.0, trend_pull))


def generate_idea(studio, week: int, rng: random.Random, author, origin: str = "team",
                  inspiration_game=None, franchise_id: int | None = None) -> RoughIdea:
    """Create one rough idea from an employee's head (or a released game)."""
    activity, setting, fantasy, hook, trend_pull = _pick_components(rng, author)
    trait = _trait_bias(getattr(author, "trait", ""))
    quirk = _quirk_bias(getattr(author, "quirk", ""))
    team_size = max(1, len(studio.team))
    disagreement = 0.12 if team_size >= 4 and rng.random() < 0.35 else 0.0
    clarity = 0.45 + author.morale / 240 - max(0.0, author.fatigue - 55) / 85 + trait["clarity"] + quirk.get("clarity", 0.0) - disagreement
    originality = 0.48 - trend_pull * 0.22 + trait["originality"] + quirk.get("originality", 0.0) + (0.10 if hook else 0.0)
    avg_code = sum(member.code for member in studio.team) / team_size
    doubt = 0.18 + (hook.doubt if hook else 0.0) + max(0.0, (55 - avg_code) / 110)
    if inspiration_game is not None:
        # Inspired ideas reuse the market identity of the released game.
        genre = inspiration_game.genre
        secondary_genre = inspiration_game.secondary_genre or inspiration_game.genre
        topic = inspiration_game.topic
        secondary_topic = inspiration_game.secondary_topic or inspiration_game.topic
        originality = min(1.0, originality - 0.08)  # sequels lean familiar
        doubt = max(0.05, doubt - 0.12)
    else:
        genre = _validate(activity.genre, GENRES, "genre")
        secondary_genre = _validate(activity.secondary_genre, GENRES, "genre")
        topic = _validate(setting.topics[0], TOPICS, "topic")
        secondary_topic = _validate(setting.topics[-1], TOPICS, "topic")
    tags = sorted(set(activity.tags) | set(setting.tags) | set(hook.tags if hook else ()))
    lifetime = int(6 + (1 - trend_pull) * 26 + rng.uniform(0, 6))
    return RoughIdea(
        idea_id=studio.next_idea_id,
        title=_idea_title(rng),
        fantasy=fantasy.text,
        activity=activity.name,
        setting=setting.name,
        hook=hook.name if hook else "",
        uncertainty=hook.uncertainty if hook else f"What makes {activity.name.split(' ', 1)[-1]} enjoyable for hours?",
        source=author.name,
        origin=origin,
        genre=genre,
        secondary_genre=secondary_genre,
        topic=topic,
        secondary_topic=secondary_topic,
        clarity=max(0.05, min(1.0, clarity)),
        originality=max(0.05, min(1.0, originality)),
        technical_doubt=max(0.02, min(1.0, doubt)),
        trend_pull=trend_pull,
        created_week=week,
        cool_at_week=week + max(5, lifetime),
        inspiration_game_id=inspiration_game.game_id if inspiration_game is not None else None,
        franchise_id=franchise_id,
        tags=tags,
    )


def shelf_capacity(studio) -> int:
    return min(8, 3 + len(studio.team))


def active_idea_count(studio) -> int:
    """Dormant ideas are cold storage; they do not crowd out new pitches."""
    return sum(1 for idea in studio.idea_shelf if idea.status in ("fresh", "cooling"))


def _member_available(member) -> bool:
    return member.vacation_weeks_left == 0 and member.burnout_weeks_left == 0


def process_ideas_week(studio, week: int, rng: random.Random, log) -> None:
    """Weekly idea lifecycle: generation, cooling, dormancy, revival."""
    capacity = shelf_capacity(studio)
    for idea in studio.idea_shelf:
        if idea.status == "fresh" and week >= idea.cool_at_week - max(2, (idea.cool_at_week - idea.created_week) // 3):
            idea.status = "cooling"
        elif idea.status == "cooling" and week >= idea.cool_at_week:
            idea.status = "dormant"
            log(f"{idea.title} cooled off on the shelf. It may return later.")
        elif idea.status == "dormant" and active_idea_count(studio) < capacity and rng.random() < 0.03:
            idea.status = "fresh"
            idea.created_week = week
            idea.cool_at_week = week + int(8 + rng.uniform(0, 8))
            idea.clarity = max(0.3, idea.clarity - 0.05)
            log(f"{idea.title} resurfaced from the shelf with new eyes.")
    if active_idea_count(studio) >= capacity:
        return
    for member in studio.team:
        if not _member_available(member) or member.fatigue >= 90:
            continue
        chance = 0.055 + member.research / 2500 + (0.02 if member.founder else 0.0)
        if member.fatigue > 70:
            chance *= 0.5
        if rng.random() < chance:
            idea = generate_idea(studio, week, rng, member)
            studio.idea_shelf.append(idea)
            studio.next_idea_id += 1
            signals = ", ".join(idea.signal_words()[:2])
            log(f"{member.name} jotted down an idea: {idea.title} ({signals}).")
            if len(studio.idea_shelf) >= capacity:
                break


def inspire_from_release(studio, week: int, rng: random.Random, game, log) -> None:
    """A release plants follow-up ideas (sequel-flavoured) on the shelf."""
    if active_idea_count(studio) >= shelf_capacity(studio) or not studio.team:
        return
    authors = [member for member in studio.team if _member_available(member)] or studio.team
    author = max(authors, key=lambda member: member.design + member.art)
    if rng.random() < 0.75:
        idea = generate_idea(studio, week, rng, author, origin="release", inspiration_game=game,
                             franchise_id=game.franchise_id)
        studio.idea_shelf.append(idea)
        studio.next_idea_id += 1
        log(f"Playing {game.title} again sparked an idea: {idea.title}.")


def inspire_from_contract(studio, week: int, rng: random.Random, contract_name: str, log) -> None:
    if active_idea_count(studio) >= shelf_capacity(studio) or not studio.team:
        return
    if rng.random() < 0.25:
        author = rng.choice(studio.team)
        idea = generate_idea(studio, week, rng, author, origin="contract")
        studio.idea_shelf.append(idea)
        studio.next_idea_id += 1
        log(f"The {contract_name} contract gave {author.name} an idea: {idea.title}.")


def force_idea(studio, week: int, rng: random.Random, genre: str, topic: str,
               hook: str = "", source: str = "You") -> RoughIdea:
    """Deterministic helper used by tests and scenario setups."""
    author = studio.team[0] if studio.team else None
    idea = generate_idea(studio, week, rng, author or type("A", (), {"name": source})(), origin="team")
    idea.genre = genre
    idea.topic = topic
    idea.secondary_genre = genre
    idea.secondary_topic = topic
    if hook:
        match = next((h for h in HOOKS if h.name == hook), None)
        idea.hook = match.name if match else hook
        idea.uncertainty = match.uncertainty if match else "Will the hook hold up?"
        idea.technical_doubt = max(idea.technical_doubt, match.doubt if match else 0.4)
        idea.tags = sorted(set(idea.tags) | set(match.tags if match else ()))
    return idea


# ---------------------------------------------------------------------------
# Concept experiments
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Experiment:
    key: str
    name: str
    blurb: str
    weeks: int
    skill: str  # which team skill drives the finding
    requires_tags: frozenset[str] | None = None
    requires_hook: bool = False
    requires_doubt: float = 0.0


EXPERIMENTS: tuple[Experiment, ...] = (
    Experiment("paper_prototype", "Paper prototype", "Sketch the core rules on paper and argue through a full round.", 1, "design"),
    Experiment("playable_prototype", "Playable prototype", "Program the roughest possible build of the central activity.", 2, "code"),
    Experiment("test_activity", "Activity test", "Prototype only the main verb and time how long it stays interesting.", 1, "design"),
    Experiment("explore_hook", "Hook exploration", "Build a tiny scene around the unusual hook and watch what happens.", 1, "design", requires_hook=True),
    Experiment("visual_study", "Look & sound study", "Produce a small visual and audio study of the setting.", 1, "art"),
    Experiment("tech_spike", "Technical spike", "Prototype the riskiest technical piece in isolation.", 2, "code", requires_doubt=0.35),
    Experiment("player_pitch", "Pitch test", "Walk potential players through the pitch and note what they think it is.", 1, "research"),
)


def available_experiments(idea: RoughIdea) -> list[Experiment]:
    chosen = []
    for experiment in EXPERIMENTS:
        if experiment.requires_hook and not idea.hook:
            continue
        if experiment.requires_doubt and idea.technical_doubt < experiment.requires_doubt:
            continue
        chosen.append(experiment)
    return chosen


def _team_skill(team, skill: str) -> float:
    if not team:
        return 30.0
    values = {
        "design": [member.design for member in team],
        "code": [member.code for member in team],
        "art": [member.art for member in team],
        "audio": [member.audio for member in team],
        "research": [member.research for member in team],
    }[skill]
    return sum(values) / len(values)


def experiment_duration(idea: RoughIdea, experiment: Experiment, team) -> int:
    """Capable teams finish studies faster; weak teams overrun."""
    capability = _team_skill(team, experiment.skill)
    extra = 1 if capability < 34 else 0
    return experiment.weeks + extra


def experiment_confidence(idea: RoughIdea, experiment: Experiment, team, rng: random.Random) -> str:
    capability = _team_skill(team, experiment.skill) / 100
    score = capability * 0.7 + rng.random() * 0.35
    if experiment.skill == "research":
        score += 0.05
    if score >= 0.75:
        return "Reasonable" if rng.random() < 0.65 else "Strong"
    if score >= 0.45:
        return "Reasonable" if rng.random() < 0.5 else "Weak"
    return "Weak"


def experiment_by_key(key: str) -> Experiment:
    return next(item for item in EXPERIMENTS if item.key == key)


# ---------------------------------------------------------------------------
# Presentation directions (Design stage)
# ---------------------------------------------------------------------------


FORMS = ("2D sprites", "2.5D models", "Full 3D", "Pre-rendered", "Voxel")
STYLES = ("Pixel art", "Hand-drawn", "Vector flat", "Painted", "Low-poly", "Cel-shaded", "Monochrome", "Degraded retro")
CAMERAS = ("Side-view", "Top-down", "Isometric", "Third-person", "First-person", "Fixed cinematic")
MOVEMENTS = ("Flat plane", "Layered lanes", "Limited depth", "Free 3D")
DENSITIES = ("Minimal", "Readable", "Detailed", "Cinematic")

_FORM_WORK = {"2D sprites": 1.00, "2.5D models": 1.15, "Full 3D": 1.30, "Pre-rendered": 1.05, "Voxel": 1.10}
_STYLE_WORK = {"Pixel art": 0.92, "Hand-drawn": 1.20, "Vector flat": 0.95, "Painted": 1.25,
               "Low-poly": 1.00, "Cel-shaded": 1.05, "Monochrome": 0.85, "Degraded retro": 0.90}
_CAMERA_WORK = {"Side-view": 0.95, "Top-down": 0.90, "Isometric": 1.00, "Third-person": 1.10,
                "First-person": 1.15, "Fixed cinematic": 0.90}
_MOVEMENT_WORK = {"Flat plane": 1.00, "Layered lanes": 0.95, "Limited depth": 1.05, "Free 3D": 1.25}


def presentation_work_multiplier(form: str, style: str, camera: str, movement: str) -> float:
    return round(_FORM_WORK.get(form, 1.1) * _STYLE_WORK.get(style, 1.0) * _CAMERA_WORK.get(camera, 1.0) * _MOVEMENT_WORK.get(movement, 1.0), 3)


def _package(form: str, style: str, camera: str, movement: str, density: str, note: str, fit: float) -> dict:
    return {
        "name": f"{style} {form.split(' ', 1)[0]} / {camera.lower()}",
        "form": form,
        "style": style,
        "camera": camera,
        "movement": movement,
        "density": density,
        "work": presentation_work_multiplier(form, style, camera, movement),
        "note": note,
        "fit": fit,
    }


def presentation_packages(idea) -> list[dict]:
    """3-4 coherent presentation directions derived from the idea's tags."""
    tags = set(getattr(idea, "tags", ()) or ())
    reflex = bool({"reflex", "competition"} & tags)
    systems = bool({"systems", "management"} & tags)
    story = bool({"narrative"} & tags)
    gentle = bool({"gentle", "creation"} & tags)
    atmosphere = bool({"atmosphere"} & tags)
    packages = []
    if reflex:
        packages.append(_package("2D sprites", "Pixel art", "Side-view", "Flat plane", "Readable",
                                 "Reads instantly; modest asset load; animation-heavy.", 0.9))
        packages.append(_package("Full 3D", "Low-poly", "Third-person", "Free 3D", "Detailed",
                                 "Distinct space and movement; navigation and camera risk.", 0.7))
    if systems or gentle:
        packages.append(_package("2D sprites", "Vector flat", "Isometric", "Flat plane", "Detailed",
                                 "Clear systemic spaces; moderate asset workload.", 0.85))
    if story or atmosphere:
        packages.append(_package("2D sprites", "Hand-drawn", "Fixed cinematic", "Flat plane", "Cinematic",
                                 "Strong expression; heavy animation workload.", 0.8))
    if systems and atmosphere:
        packages.append(_package("Full 3D", "Cel-shaded", "Isometric", "Limited depth", "Detailed",
                                 "Modern look over deep systems; model and camera work.", 0.75))
    if atmosphere and not reflex:
        packages.append(_package("Pre-rendered", "Painted", "Fixed cinematic", "Limited depth", "Cinematic",
                                 "Painted atmosphere; inflexible scenes.", 0.7))
    if gentle and not atmosphere:
        packages.append(_package("2D sprites", "Pixel art", "Top-down", "Flat plane", "Minimal",
                                 "Cheap, readable and cozy; limited visual ambition.", 0.8))
    if not packages:
        packages.append(_package("2D sprites", "Pixel art", "Top-down", "Flat plane", "Readable",
                                 "A safe, readable default for an unclear concept.", 0.5))
    return packages[:4]


def resolve_presentation_choice(state, packages: list[dict]) -> dict:
    """The selected package with any axis tweaks applied."""
    base = dict(packages[state.selected_presentation % max(1, len(packages))])
    for key in ("form", "style", "camera", "movement", "density"):
        override = state.design_tweaks.get(key)
        if override:
            base[key] = override
    base["work"] = presentation_work_multiplier(base["form"], base["style"], base["camera"], base["movement"])
    return base


def resolve_experiment(idea, experiment: Experiment, team, week: int, rng: random.Random) -> dict:
    """Produce a finding — evidence, not a guaranteed improvement."""
    confidence = experiment_confidence(idea, experiment, team, rng)
    capability = _team_skill(team, experiment.skill) / 100
    roll = rng.random() + capability * 0.45
    flags: dict = {}
    subject = idea.setting
    verb = idea.activity

    if experiment.key == "paper_prototype":
        if roll > 0.85:
            text = f"The rules hold together on paper: {verb} produces real decisions."
            flags["fun_core"] = True
        elif roll > 0.45:
            text = f"The loop works on paper but the middle of a session sags. Why {idea.uncertainty.lower()} is still open."
            flags["fun_core"] = None
        else:
            text = f"On paper the rules collapse into busywork. The central activity needs a sharper reason to exist."
            flags["fun_core"] = False
    elif experiment.key == "playable_prototype":
        if roll > 0.8:
            text = f"The playable build is ugly but fun: {verb} already creates stories."
            flags["fun_core"] = True
        elif roll > 0.5:
            text = f"The first run is fun, the fourth is not. Repetition is the open problem."
            flags["fun_core"] = True
            flags["repetition"] = True
        else:
            text = f"The build plays, but nothing in it pulls players forward yet."
            flags["fun_core"] = False
    elif experiment.key == "test_activity":
        if roll > 0.8:
            text = f"The main verb alone carries attention for a full session."
            flags["fun_core"] = True
        elif roll > 0.45:
            text = f"The verb works in short bursts but needs a structure to lean on."
            flags["fun_core"] = None
        else:
            text = f"The main activity gets old within minutes in its current form."
            flags["fun_core"] = False
    elif experiment.key == "explore_hook":
        if roll > 0.75:
            text = f"The hook — {idea.hook} — is the most memorable thing tested. Players ask for more of it."
            flags["hook_strength"] = "strong"
        elif roll > 0.4:
            text = f"The hook shows promise but currently fights the main activity instead of feeding it."
            flags["hook_strength"] = None
        else:
            text = f"The hook confuses more than it intrigues. It may not survive contact with production."
            flags["hook_strength"] = "weak"
    elif experiment.key == "visual_study":
        if roll > 0.75:
            text = f"The {subject} study lands: testers immediately read the tone from a single frame."
            flags["look"] = "strong"
        elif roll > 0.4:
            text = f"The study looks right in stills but the palette gets muddy in motion."
            flags["look"] = None
        else:
            text = f"The look does not say anything yet. The setting reads generic in motion."
            flags["look"] = "weak"
    elif experiment.key == "tech_spike":
        if roll > 0.7:
            text = f"The technical risk is real but solvable with the current team and a plan."
            flags["tech_risk"] = "viable"
        elif roll > 0.4:
            text = f"The spike half-works. It needs more research before anyone should promise it."
            flags["tech_risk"] = None
        else:
            text = f"The spike failed in every configuration tried. Treat the technique as missing, not unproven."
            flags["tech_risk"] = "blocked"
    else:  # player_pitch
        if roll > 0.75:
            text = f"Pitch readers described the game the way the studio hopes they would."
            flags["audience"] = "warm"
        elif roll > 0.4:
            text = f"Pitch readers got the setting but not the point. The fantasy needs one clearer sentence."
            flags["audience"] = None
        else:
            text = f"Pitch readers invent a different game than intended. The pitch is misleading."
            flags["audience"] = "cold"
    return {
        "week": week,
        "experiment": experiment.name,
        "text": text,
        "confidence": confidence,
        "flags": flags,
    }
