# all turrets should be in state 0 for the user to win the game
#
# Each turret i has n_i states (0 .. n_i-1). Each button j rotates turret i by
# a_ij steps (mod n_i). Pressing button j x_j times leaves turret i in state
#     s_i + sum_j a_ij * x_j   (mod n_i)
# so solving the puzzle means solving the system of linear congruences
#     sum_j a_ij * x_j  ==  -s_i   (mod n_i)     for every turret i
# with a different modulus per row. That is done in game_solution() with an
# exact integer Gauss-Jordan elimination (Hermite normal form), not floats.

import random
import time
from math import gcd


def lcm(a, b):
    return a * b // gcd(a, b)


def extended_gcd(a, b):
    # returns (g, x, y) with a*x + b*y == g == gcd(a, b), g >= 0
    old_r, r = a, b
    old_x, x = 1, 0
    old_y, y = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_x, x = x, old_x - q * x
        old_y, y = y, old_y - q * y
    if old_r < 0:
        old_r, old_x, old_y = -old_r, -old_x, -old_y
    return old_r, old_x, old_y


class Turret:
    def __init__(self, name, nbr_stats, start_stat):
        self.name = name
        self.nbr_stats = nbr_stats
        self.start_stat = start_stat
        self.current_stat = start_stat


class Button:
    def __init__(self, name, associated_turrets):
        self.name = name
        # self.associated_turrets is a dictionary, its keys are the turrets and the value is
        # the number of rotations that will be applied to the turret: {turret: value}
        self.associated_turrets = associated_turrets

    def on_click(self, times=1):
        for t, rotation in self.associated_turrets.items():
            t.current_stat = (t.current_stat + rotation * times) % t.nbr_stats

    def order(self):
        # number of presses after which this button brings every turret back where it was
        result = 1
        for t, rotation in self.associated_turrets.items():
            result = lcm(result, t.nbr_stats // gcd(rotation, t.nbr_stats))
        return result


class Game:
    def __init__(self):
        # to win the game, the state of the turrets should be 0
        self.turrets = []
        # each button rotates one or multiple turrets
        self.buttons = []
        self.moves = 0

    def start_gamemode_shuffle(self, min_turrets=3, max_turrets=10, min_buttons=3, max_buttons=10, verbose=False):
        start = time.time()
        self.turrets = []
        self.buttons = []
        self.moves = 0

        nbr_turret = random.randint(min_turrets, max_turrets)
        for i in range(nbr_turret):
            nbr_stats = random.randint(2, 10)
            self.turrets.append(Turret(f"turret_{i+1}", nbr_stats, 0))

        nbr_buttons = random.randint(min_buttons, max_buttons)
        for i in range(nbr_buttons):
            associated_turrets = {t: random.randint(0, t.nbr_stats - 1) for t in self.turrets}
            self.buttons.append(Button(f"button_{i+1}", associated_turrets))

        # Random start states are usually unsolvable (the buttons don't span every
        # configuration), so scramble from the solved position instead: press random
        # buttons a random number of times. Undoing that is always possible.
        while all(t.current_stat == 0 for t in self.turrets):
            for btn in self.buttons:
                btn.on_click(random.randint(0, btn.order() - 1))
        for t in self.turrets:
            t.start_stat = t.current_stat

        if verbose:
            print(f"{nbr_turret} turrets / {nbr_buttons} buttons created - time: {time.time()-start:.4f}s")

    def is_won(self):
        return all(t.current_stat == 0 for t in self.turrets)

    def on_click_button(self, btn):
        btn.on_click()
        self.moves += 1
        return self.is_won()

    def reset(self):
        for t in self.turrets:
            t.current_stat = t.start_stat
        self.moves = 0

    def game_solution(self):
        """Return {button_name: presses} that brings every turret to 0 from the
        current state, or None if no solution exists.

        Unknowns: x_j (presses of button j) and y_i (wrap-arounds of turret i).
        The congruences become one exact integer system
            [ A | diag(n) ] . [x; y] = -s
        which is brought to lower-triangular (Hermite) form with unimodular column
        operations built from the extended gcd -- the integer equivalent of
        Gauss-Jordan pivoting, since division is not available modulo n.
        """
        m, k = len(self.turrets), len(self.buttons)
        if m == 0:
            return {}
        cols = k + m
        H = [[btn.associated_turrets[t] for btn in self.buttons] + [t.nbr_stats if r == i else 0 for r in range(m)]
             for i, t in enumerate(self.turrets)]
        b = [(-t.current_stat) % t.nbr_stats for t in self.turrets]
        # U tracks the column operations: H_original . U == H
        U = [[int(r == c) for c in range(cols)] for r in range(cols)]

        def combine(c1, c2, a11, a21, a12, a22):
            # col c1 <- a11*c1 + a21*c2 ; col c2 <- a12*c1 + a22*c2
            for mat in (H, U):
                for row in mat:
                    v1, v2 = row[c1], row[c2]
                    row[c1] = a11 * v1 + a21 * v2
                    row[c2] = a12 * v1 + a22 * v2

        for r in range(m):
            # pivot on column r: fold the gcd of row r (columns r..) into it
            for c in range(r + 1, cols):
                if H[r][c] == 0:
                    continue
                p, q = H[r][r], H[r][c]
                g, x, y = extended_gcd(p, q)
                # determinant x*(p/g) + y*(q/g) == 1, so the operation is invertible over Z
                combine(r, c, x, y, -q // g, p // g)
            if H[r][r] < 0:
                for mat in (H, U):
                    for row in mat:
                        row[r] = -row[r]
            # Gauss-Jordan step: reduce row r to the left of the pivot (keeps numbers small)
            for c in range(r):
                f = H[r][c] // H[r][r]
                if f:
                    for mat in (H, U):
                        for row in mat:
                            row[c] -= f * row[r]

        # forward substitution on the lower-triangular system H . w = b
        w = [0] * cols
        for r in range(m):
            rest = b[r] - sum(H[r][c] * w[c] for c in range(r))
            if rest % H[r][r] != 0:
                return None
            w[r] = rest // H[r][r]

        orders = [btn.order() for btn in self.buttons]
        presses = [sum(U[j][c] * w[c] for c in range(cols)) % orders[j] for j in range(k)]

        # The remaining columns of U (r >= m) span every combination of presses that
        # changes nothing. Use them to shrink the total number of presses.
        kernel = [[U[j][c] for j in range(k)] for c in range(m, cols)]
        kernel = [v for v in kernel if any(v[j] % orders[j] for j in range(k))]
        improved = True
        while improved:
            improved = False
            for v in kernel:
                period = 1
                for j in range(k):
                    period = lcm(period, orders[j] // gcd(v[j], orders[j]))
                best, best_t = sum(presses), 0
                for t in range(1, period):
                    total = sum((presses[j] + t * v[j]) % orders[j] for j in range(k))
                    if total < best:
                        best, best_t = total, t
                if best_t:
                    presses = [(presses[j] + best_t * v[j]) % orders[j] for j in range(k)]
                    improved = True

        return {btn.name: presses[j] for j, btn in enumerate(self.buttons)}

    def shortest_solution(self, max_states=300_000):
        """Fewest-presses solution via bidirectional breadth-first search: from the
        current state forward and from the solved state backward, one layer at a
        time, until both searches meet. Returns None if the search grows past
        max_states (huge boards) so the caller can fall back to game_solution()."""
        ns = [t.nbr_stats for t in self.turrets]
        rots = [[btn.associated_turrets[t] for t in self.turrets] for btn in self.buttons]
        start = tuple(t.current_stat for t in self.turrets)
        goal = tuple(0 for _ in self.turrets)
        if start == goal:
            return {btn.name: 0 for btn in self.buttons}

        # seen[side][state] = (depth, previous state, button used)
        seen = [{start: (0, None, None)}, {goal: (0, None, None)}]
        frontiers = [[start], [goal]]
        while frontiers[0] and frontiers[1]:
            side = 0 if len(frontiers[0]) <= len(frontiers[1]) else 1
            sign = 1 if side == 0 else -1  # the backward search undoes presses
            own, other = seen[side], seen[1 - side]
            best, best_state = None, None
            new_frontier = []
            for s in frontiers[side]:
                depth = own[s][0] + 1
                for j, r in enumerate(rots):
                    nxt = tuple((a + sign * b) % n for a, b, n in zip(s, r, ns))
                    if nxt in own:
                        continue
                    own[nxt] = (depth, s, j)
                    new_frontier.append(nxt)
                    if nxt in other and (best is None or depth + other[nxt][0] < best):
                        best, best_state = depth + other[nxt][0], nxt
            if best_state is not None:
                presses = [0] * len(self.buttons)
                for table in seen:
                    s = best_state
                    while table[s][1] is not None:
                        presses[table[s][2]] += 1
                        s = table[s][1]
                return {btn.name: presses[j] for j, btn in enumerate(self.buttons)}
            if len(seen[0]) + len(seen[1]) > max_states:
                return None
            frontiers[side] = new_frontier
        return None

    def best_solution(self):
        """Returns (solution, is_shortest). Gauss-Jordan decides whether a solution
        exists; the search then tries to find the shortest one."""
        solution = self.game_solution()
        if solution is None:
            return None, False
        shortest = self.shortest_solution()
        if shortest is not None:
            return shortest, True
        return solution, False

    def check_solution(self, solution):
        # replay the solution on a copy of the current states
        stats = {t: t.current_stat for t in self.turrets}
        for btn in self.buttons:
            for t, rotation in btn.associated_turrets.items():
                stats[t] = (stats[t] + rotation * solution.get(btn.name, 0)) % t.nbr_stats
        return all(v == 0 for v in stats.values())

    def to_dict(self):
        return {
            "turrets": [{"name": t.name, "nbr_stats": t.nbr_stats, "start_stat": t.start_stat,
                         "current_stat": t.current_stat} for t in self.turrets],
            "buttons": [{"name": btn.name, "rotations": [btn.associated_turrets[t] for t in self.turrets]}
                        for btn in self.buttons],
            "moves": self.moves,
            "won": self.is_won(),
        }


def play_console():
    game = Game()
    game.start_gamemode_shuffle(verbose=True)
    while not game.is_won():
        print("\n" + "  ".join(f"{t.name}: {t.current_stat}/{t.nbr_stats}" for t in game.turrets))
        for i, btn in enumerate(game.buttons):
            effects = ", ".join(f"+{v}" for v in btn.associated_turrets.values())
            print(f"  [{i+1}] {btn.name}: {effects}")
        choice = input("button number (s = solution, q = quit): ").strip().lower()
        if choice == "q":
            return
        if choice == "s":
            print(game.game_solution())
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(game.buttons):
            game.on_click_button(game.buttons[int(choice) - 1])
    print(f"\nAll turrets at 0 - you win in {game.moves} moves!")


if __name__ == "__main__":
    play_console()
