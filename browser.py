"""Local browser client. No curses, third-party packages, or external assets."""
import argparse
from dataclasses import asdict
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import secrets
import time
import webbrowser

import simulation as sim


FIELDS = {
    "selected_scope": sim.SCOPES, "selected_format": sim.GAME_FORMATS,
    "selected_audience": sim.AUDIENCES, "selected_creative_primary": sim.CREATIVE_DIRECTIONS,
    "selected_creative_secondary": sim.CREATIVE_DIRECTIONS,
    "selected_monetization": sim.MONETIZATION_MODELS, "selected_price": sim.PRICE_POINTS,
    "selected_announcement": sim.ANNOUNCEMENT_STRATEGIES,
    "selected_release_policy": sim.RELEASE_POLICIES,
    "selected_release_strategy": sim.RELEASE_STRATEGIES,
    "selected_marketing": sim.MARKETING, "selected_channel": sim.CHANNELS,
}


class BrowserGame:
    def __init__(self, save_path):
        self.save_path = str(save_path)
        self.state = None
        self.overlay = False
        self.last_tick = time.monotonic()
        self.last_contact = self.last_tick

    def hold_reason(self):
        if not self.state:
            return "No studio open"
        p = self.state.studio.current_project
        if self.state.studio.cash < 0:
            return "Financing required"
        if p and p.pending_decision is not None:
            return "Production decision"
        if self.overlay:
            return "Popup open"
        if time.monotonic() - self.last_contact > 3:
            return "Browser disconnected"
        return ""

    def tick(self, now=None):
        now = time.monotonic() if now is None else now
        elapsed = max(0, min(now - self.last_tick, 0.5))
        self.last_tick = now
        if not self.state or self.hold_reason():
            return
        s = self.state
        # Consume time one day at a time, stopping immediately at decisions.
        seconds = elapsed * sim.TIME_SPEEDS[s.time_speed_index]
        while seconds > 0 and not self.hold_reason() and s.time_speed_index:
            step = min(seconds, sim.SECONDS_PER_DAY - s.clock.elapsed_seconds)
            days = s.clock.update(step)
            seconds -= step
            if days:
                sim.advance_days(s, days)

    def view(self):
        if self.state is None:
            return {"started": False, "can_load": Path(self.save_path).is_file()}
        s = self.state
        p = s.studio.current_project
        studio = asdict(s.studio)
        if p:
            studio['current_project'].update(phase=p.phase, progress=p.progress,
                                             bug_progress=p.bug_progress,
                                             remaining_work=p.remaining_work,
                                             weekly_output=sim.projected_weekly_output(s.studio, p.focus))
        for released, display in zip(s.studio.catalog, studio['catalog']):
            sale = sim.sale_for_game(s.studio, released.game_id)
            display.update(weekly_units=round(sale.weekly_units) if sale else 0,
                           week_to_date=sale.week_to_date if sale else 0,
                           profit=sim.game_profit(released))
        # Browser view model: explicit display amounts, not inferred fallbacks.
        for employee in studio['team'] + studio['applicants']:
            employee['salary'] = employee['annual_salary']
        for contract in studio['contract_offers'] + ([studio['contract']] if studio['contract'] else []):
            contract['pay'] = contract['payout']
        if s.studio.active_research:
            job = s.studio.active_research
            node = next(n for n in sim.RESEARCH_NODES if n['key'] == job.node_key)
            studio['active_research'].update(name=node['name'], effect=node['effect'], progress=job.progress)
        loans = [{**offer, 'amount': offer['principal'],
                  'description': f"{offer['weeks']} weeks · {offer['rate']:.0%} interest"}
                 for offer in sim.LOAN_OFFERS]
        experiments = sim.idea_engine.available_experiments(sim.concept_idea_view(p)) if p and p.stage == "concept" else []
        def research_lock(key):
            node = sim.research_by_key(key) if key else None
            return f"Requires {node['name']}" if key and not sim.has_research(s.studio, key) and node else ''
        return {
            "started": True, "studio": studio, "date": str(s.clock.current_date),
            "clock": {"progress": s.clock.progress, "week": s.clock.week,
                      "speed": s.time_speed_index, "held": self.hold_reason(),
                      "weeks_per_second": sim.TIME_SPEEDS[s.time_speed_index] / sim.SECONDS_PER_WEEK},
            "allocations": sim.activity_allocations(s.studio),
            "projected_output": sim.projected_weekly_output(s.studio, p.focus if p else (0, 0, 0, 0)),
            "monthly_cost": sim.monthly_fixed_cost(s.studio),
            "cost_breakdown": sim.monthly_cost_breakdown(s.studio),
            "market_chart": [asdict(entry) for entry in sim.market_chart(s, 30)],
            "runway": sim.runway_months(s.studio), "logs": s.logs[:30],
            "drains": sim.capacity_drains(s.studio),
            "experiments": [asdict(e) for e in experiments],
            "options": {k: [{"name": v["name"], "index": i} for i, v in enumerate(values)] for k, values in FIELDS.items()},
            "plan": {k: getattr(s, k) for k in FIELDS},
            "presentation": s.selected_presentation,
            "requirements": sim.plan_requirements(s) if p and p.stage == "design" else [],
            "research": sim.RESEARCH_NODES, "loans": loans,
            "promotions": [{**x, 'lock': research_lock(sim.research_requirement_for_promotion(x['key'])) or (f"Requires {x['rep']} player trust" if s.studio.reputation < x['rep'] else '')} for x in sim.PROMOTIONS],
            "update_sizes": [{**x, 'lock': research_lock(sim.research_requirement_for_update(x['name']))} for x in sim.UPDATE_SIZES], "update_focuses": sim.UPDATE_FOCUSES,
            "community_actions": sim.COMMUNITY_ACTIONS,
            "decision": sim.PRODUCTION_DECISIONS[p.pending_decision] if p and p.pending_decision is not None else None,
        }

    def action(self, data):
        action = data.get("action")
        if action == "new":
            if self.state is not None:
                raise ValueError("Restart the server to start another studio; save your current game first.")
            self.state = sim.GameState.new_campaign(save_path=self.save_path)
            return
        if action == "load":
            if self.state is not None:
                raise ValueError("A studio is already open.")
            self.state = sim.load_game(self.save_path)
            return
        s = self.state
        if s is None:
            raise ValueError("Start or load a studio first.")
        p = s.studio.current_project
        index = data.get("index", 0)
        if type(index) is not int or index < 0:
            raise ValueError("Invalid selection.")
        if action == "save":
            sim.save_game(s)
        elif action == "overlay":
            self.overlay = bool(data.get("open"))
        elif action == "pause":
            if s.time_speed_index:
                s.resume_speed_index = s.time_speed_index
                s.time_speed_index = 0
            else:
                s.time_speed_index = max(1, s.resume_speed_index)
        elif action == "speed":
            if index >= len(sim.TIME_SPEEDS):
                raise ValueError("Invalid speed.")
            s.time_speed_index = index
            if index:
                s.resume_speed_index = index
        elif action == "advance":
            for _ in range(7 if data.get("week") else 1):
                p = s.studio.current_project
                if s.studio.cash < 0 or (p and p.pending_decision is not None):
                    s.log("Time held: review the outstanding studio decision first.")
                    break
                s.clock.current_date += timedelta(days=1)
                s.clock.day += 1
                s.clock.week = (s.clock.day - 1) // 7 + 1
                sim.advance_days(s, 1)
        elif action == "idea":
            sim.start_concept_project(s, s.studio.idea_shelf[index])
        elif action == "experiment" and p and p.stage == "concept":
            options = sim.idea_engine.available_experiments(sim.concept_idea_view(p))
            sim.start_experiment(s, options[index].key)
        elif action == "design":
            speed = s.time_speed_index
            sim.begin_design_review(s)
            # Curses opens its own blocking review. Browser overlays own their
            # pause lifetime; an uncommitted design must not freeze the world.
            s.time_speed_index = speed
            s.design_review_resume_on_close = False
        elif action == "shelve":
            sim.shelve_concept(s)
        elif action == "plan" and p and p.stage == "design":
            field = data.get("field")
            if field not in FIELDS or index >= len(FIELDS[field]):
                raise ValueError("Invalid plan option.")
            setattr(s, field, index)
        elif action == "presentation" and p and p.stage == "design":
            if index >= len(p.gdd.get("presentation_options", [])):
                raise ValueError("Invalid presentation.")
            s.selected_presentation = index
        elif action == "commit":
            speed = s.time_speed_index
            sim.commit_design_plan(s)
            s.time_speed_index = speed
        elif action == "decision":
            sim.resolve_project_decision(s, index)
        elif action == "release":
            sim.release_ready_project(s)
        elif action == "hire":
            s.selected_employee = index
            sim.hire_candidate(s)
        elif action == "vacation":
            sim.start_employee_vacation(s, s.studio.team[index])
        elif action == "contract":
            sim.accept_contract_offer(s, index)
        elif action == "research":
            sim.queue_research(s, sim.RESEARCH_NODES[index]["key"])
        elif action == "loan":
            sim.take_loan(s, index)
        elif action in ("marketing", "community"):
            game_id = data.get('game_id')
            if type(game_id) is not int or not (game_id == 0 and p or any(g.game_id == game_id for g in s.studio.catalog)):
                raise ValueError('Choose a current project or released game.')
            choices = sim.PROMOTIONS if action == 'marketing' else sim.COMMUNITY_ACTIONS
            if index >= len(choices):
                raise ValueError('Invalid campaign selection.')
            operation = sim.buy_promotion if action == 'marketing' else sim.take_community_action
            if not operation(s, game_id, index):
                raise ValueError(s.logs[0])
        elif action in ("update", "support", "promote", "release_update", "price"):
            game = s.studio.catalog[index]
            if action == 'release_update':
                size, focus = data.get('size'), data.get('focus')
                if size not in [x['name'] for x in sim.UPDATE_SIZES] or focus not in [x['name'] for x in sim.UPDATE_FOCUSES]:
                    raise ValueError('Invalid update plan.')
                previous = game.update_size, game.update_focus
                game.update_size, game.update_focus = size, focus
                if not sim.queue_game_update(s, game.game_id):
                    game.update_size, game.update_focus = previous
                    raise ValueError(s.logs[0])
            elif action == 'price':
                delta = data.get('delta')
                if type(delta) is not int or delta not in (-1, 1):
                    raise ValueError('Invalid price change.')
                sim.cycle_game_price(s, game.game_id, delta)
            elif action == "update":
                sim.queue_game_update(s, game.game_id)
            elif action == "support":
                sim.cycle_game_support(s, game.game_id)
            else:
                sim.buy_promotion(s, game.game_id, 0)
        else:
            raise ValueError("That action is not available in this stage.")


def serve(port=8765, save_path="saves/gamedev_save.json", open_browser=True):
    game = BrowserGame(save_path)
    token = secrets.token_urlsafe(32)
    assets = Path(__file__).parent / "web"

    class Handler(BaseHTTPRequestHandler):
        def send(self, body, kind="application/json", status=200):
            self.send_response(status)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self.send(b'{}', status=403)
                return
            if self.path == "/api/state":
                game.last_contact = time.monotonic()
                self.send(json.dumps({**game.view(), "token": token}).encode())
            elif self.path in ("/", "/app.js", "/style.css", "/views.js", "/views.css"):
                name, kind = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css"), "/views.js": ("views.js", "text/javascript"), "/views.css": ("views.css", "text/css")}[self.path]
                self.send((assets / name).read_bytes(), kind)
            elif self.path in ("/fonts/JetBrainsMono-Regular.woff2", "/fonts/JetBrainsMono-SemiBold.woff2", "/fonts/JetBrainsMono-Bold.woff2"):
                self.send((assets / self.path.lstrip('/')).read_bytes(), "font/woff2")
            elif self.path in ('/operations.js', '/operations.css'):
                self.send((assets / self.path.lstrip('/')).read_bytes(), 'text/javascript' if self.path.endswith('.js') else 'text/css')
            else:
                self.send(b'{}', status=404)

        def do_POST(self):
            if self.path != "/api/action" or self.headers.get("X-Game-Token") != token:
                self.send(b'{}', status=403)
                return
            try:
                size = int(self.headers.get("Content-Length", 0))
                if not 0 < size <= 4096:
                    raise ValueError("Invalid request size.")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected an action object.")
                game.last_contact = time.monotonic()
                game.action(data)
                self.send(json.dumps({**game.view(), "token": token}).encode())
            except (ValueError, IndexError, KeyError, TypeError, OSError) as error:
                self.send(json.dumps({"error": str(error)}).encode(), status=400)

        def log_message(self, *args):
            pass

    class GameServer(HTTPServer):
        def service_actions(self):
            game.tick()

    server = GameServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Studio is available at {url}\nPress Ctrl+C to stop. Save in the browser before closing.")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--save-file", default="saves/gamedev_save.json")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    serve(args.port, args.save_file, not args.no_browser)
