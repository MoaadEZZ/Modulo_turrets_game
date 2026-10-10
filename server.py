# Web interface for the turret game: python server.py, then open http://127.0.0.1:8000
# Uses only the standard library; the game logic lives in main.py.

import json
import uuid
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from main import Game

STATIC_DIR = Path(__file__).parent / "static"
games = {}


def new_game(_payload):
    game = Game()
    game.start_gamemode_shuffle()
    game_id = uuid.uuid4().hex
    games[game_id] = game
    return {"id": game_id, **game.to_dict()}


def press(payload):
    game = games[payload["id"]]
    game.on_click_button(game.buttons[int(payload["button"])])
    return game.to_dict()


def reset(payload):
    game = games[payload["id"]]
    game.reset()
    return game.to_dict()


def solve(payload):
    game = games[payload["id"]]
    solution, shortest = game.best_solution()
    if solution is None:
        return {"solvable": False}
    return {"solvable": True, "shortest": shortest, "presses": [solution[btn.name] for btn in game.buttons]}


ROUTES = {"/api/new": new_game, "/api/press": press, "/api/reset": reset, "/api/solve": solve}


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = (STATIC_DIR / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        route = ROUTES.get(self.path)
        if route is None:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            self.send_json(200, route(payload))
        except (KeyError, IndexError, ValueError):
            self.send_json(400, {"error": "unknown game or bad request"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}"
    print(f"Turret game running on {url} (Ctrl+C to stop)")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
