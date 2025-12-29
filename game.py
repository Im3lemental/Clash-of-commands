# Clash of Commands - starter prototype (CLI)
# Run with: python game.py

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
import random


# ---------- Core enums ----------

class CardKind(str, Enum):
    TROOP = "TROOP"
    STRATEGEM = "STRATEGEM"
    AMBUSH = "AMBUSH"


class ZoneId(str, Enum):
    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"
    RESERVE = "RESERVE"
    HQ = "HQ"
    SUPPLY = "SUPPLY"


# ---------- Data models ----------

@dataclass
class TroopStats:
    str: int
    arm: int
    coh: int
    speed: int = 1
    max_ammo: int = 0


@dataclass
class Card:
    id: str
    name: str
    kind: CardKind
    text: str = ""


@dataclass
class TroopCard(Card):
    stats: TroopStats = field(default_factory=TroopStats)

    def __post_init__(self):
        self.kind = CardKind.TROOP


@dataclass
class StrategemCard(Card):
    cost_cp: int = 0

    def __post_init__(self):
        self.kind = CardKind.STRATEGEM


@dataclass
class AmbushCard(Card):
    cost_cp: int = 0
    trigger: str = "ON_ENTER"  # future-proof

    def __post_init__(self):
        self.kind = CardKind.AMBUSH


@dataclass
class Unit:
    """A troop that is on the battlefield (instance of a TroopCard)."""
    card: TroopCard
    owner: int  # 1 or 2
    zone: ZoneId
    coh: int
    ammo: int
    attacked_this_turn: bool = False

    @property
    def name(self) -> str:
        return self.card.name

    @property
    def STR(self) -> int:
        return self.card.stats.str

    @property
    def ARM(self) -> int:
        return self.card.stats.arm

    def is_alive(self) -> bool:
        return self.coh > 0


@dataclass
class Zone:
    id: ZoneId
    capacity: int
    units: List[Unit] = field(default_factory=list)

    def has_space(self) -> bool:
        return len(self.units) < self.capacity


@dataclass
class PlayerState:
    pid: int
    morale: int = 25
    cp: int = 0
    deck: List[Card] = field(default_factory=list)
    hand: List[Card] = field(default_factory=list)
    discard: List[Card] = field(default_factory=list)


# ---------- Game engine ----------

class Game:
    def __init__(self):
        self.turn = 1
        self.active_pid = 1

        self.zones: Dict[ZoneId, Zone] = {
            ZoneId.LEFT: Zone(ZoneId.LEFT, 3),
            ZoneId.CENTER: Zone(ZoneId.CENTER, 3),
            ZoneId.RIGHT: Zone(ZoneId.RIGHT, 3),
            ZoneId.RESERVE: Zone(ZoneId.RESERVE, 4),
            ZoneId.HQ: Zone(ZoneId.HQ, 2),
            ZoneId.SUPPLY: Zone(ZoneId.SUPPLY, 2),
        }

        self.adj: Dict[ZoneId, List[ZoneId]] = {
            ZoneId.HQ: [ZoneId.RESERVE],
            ZoneId.SUPPLY: [ZoneId.RESERVE],
            ZoneId.RESERVE: [ZoneId.HQ, ZoneId.SUPPLY, ZoneId.LEFT, ZoneId.CENTER, ZoneId.RIGHT],
            ZoneId.LEFT: [ZoneId.RESERVE, ZoneId.CENTER],
            ZoneId.CENTER: [ZoneId.RESERVE, ZoneId.LEFT, ZoneId.RIGHT],
            ZoneId.RIGHT: [ZoneId.RESERVE, ZoneId.CENTER],
        }

        self.p1 = PlayerState(pid=1)
        self.p2 = PlayerState(pid=2)

        self._init_sample_decks()
        self._draw_starting_hands()

    # ----- setup -----

    def _init_sample_decks(self) -> None:
        # 5 sample troops
        marines = TroopCard(
            id="troop_marines",
            name="Tactical Marines",
            kind=CardKind.TROOP,
            text="+1 STR if another Infantry is in zone (not implemented yet).",
            stats=TroopStats(str=6, arm=4, coh=6, speed=1, max_ammo=0),
        )
        scouts = TroopCard(
            id="troop_scouts",
            name="Scouts",
            kind=CardKind.TROOP,
            text="Ranged unit (ammo 2, range 1 later).",
            stats=TroopStats(str=4, arm=2, coh=4, speed=1, max_ammo=2),
        )
        cavalry = TroopCard(
            id="troop_cavalry",
            name="Assault Cavalry",
            kind=CardKind.TROOP,
            text="Fast movers.",
            stats=TroopStats(str=5, arm=3, coh=5, speed=2, max_ammo=0),
        )
        heavy = TroopCard(
            id="troop_heavy",
            name="Heavy Weapons Team",
            kind=CardKind.TROOP,
            text="Artillery-ish (ammo 2 later).",
            stats=TroopStats(str=7, arm=2, coh=4, speed=1, max_ammo=2),
        )
        elite = TroopCard(
            id="troop_elite",
            name="Elite Veterans",
            kind=CardKind.TROOP,
            text="Hard hitters.",
            stats=TroopStats(str=7, arm=4, coh=6, speed=1, max_ammo=0),
        )

        # 3 sample strategems
        suppression = StrategemCard(
            id="strat_suppression",
            name="Suppressive Fire",
            kind=CardKind.STRATEGEM,
            text="Choose a zone; enemy can't move next turn (not implemented yet).",
            cost_cp=2,
        )
        march = StrategemCard(
            id="strat_march",
            name="Forced March",
            kind=CardKind.STRATEGEM,
            text="One troop gets +1 move this turn (not implemented yet).",
            cost_cp=1,
        )
        dig_in = StrategemCard(
            id="strat_dig_in",
            name="Dig In",
            kind=CardKind.STRATEGEM,
            text="Target zone gets +1 ARM for your troops this turn (not implemented yet).",
            cost_cp=1,
        )

        # 2 sample ambushes
        killzone = AmbushCard(
            id="amb_killzone",
            name="Prepared Killzone",
            kind=CardKind.AMBUSH,
            text="When enemy enters zone: deal 3 damage to one troop (not implemented yet).",
            cost_cp=1,
            trigger="ON_ENTER",
        )
        booby = AmbushCard(
            id="amb_booby",
            name="Booby Traps",
            kind=CardKind.AMBUSH,
            text="When enemy enters zone: deal 2 damage (not implemented yet).",
            cost_cp=0,
            trigger="ON_ENTER",
        )

        # Build decks (simple repeats)
        base_deck = [
            marines, marines,
            scouts, scouts,
            cavalry, cavalry,
            heavy, heavy,
            elite, elite,
            suppression, march, dig_in,
            killzone, booby
        ]

        # Copy and shuffle per player
        self.p1.deck = base_deck[:] * 2
        self.p2.deck = base_deck[:] * 2
        random.shuffle(self.p1.deck)
        random.shuffle(self.p2.deck)

    def _draw(self, p: PlayerState, n: int = 1) -> None:
        for _ in range(n):
            if not p.deck:
                # reshuffle discard into deck
                p.deck = p.discard[:]
                p.discard.clear()
                random.shuffle(p.deck)
            if p.deck:
                p.hand.append(p.deck.pop())

    def _draw_starting_hands(self) -> None:
        self._draw(self.p1, 5)
        self._draw(self.p2, 5)

    # ----- helpers -----

    def other_pid(self, pid: int) -> int:
        return 2 if pid == 1 else 1

    def player(self, pid: int) -> PlayerState:
        return self.p1 if pid == 1 else self.p2

    def zone(self, zid: ZoneId) -> Zone:
        return self.zones[zid]

    def print_board(self) -> None:
        print("\n=== BATTLEFIELD ===")
        for zid in [ZoneId.LEFT, ZoneId.CENTER, ZoneId.RIGHT, ZoneId.RESERVE, ZoneId.HQ, ZoneId.SUPPLY]:
            z = self.zone(zid)
            units_desc = ", ".join([f"P{u.owner}:{u.name}(COH {u.coh})" for u in z.units]) or "—"
            print(f"{zid.value:8} [{len(z.units)}/{z.capacity}]: {units_desc}")
        print("===================\n")

    def print_hand(self, p: PlayerState) -> None:
        print(f"P{p.pid} Hand (CP {p.cp}, Morale {p.morale}):")
        for i, c in enumerate(p.hand, start=1):
            extra = ""
            if isinstance(c, TroopCard):
                extra = f" STR {c.stats.str} ARM {c.stats.arm} COH {c.stats.coh}"
            if isinstance(c, StrategemCard):
                extra = f" (CP {c.cost_cp})"
            if isinstance(c, AmbushCard):
                extra = f" (CP {c.cost_cp}, {c.trigger})"
            print(f"  {i}. [{c.kind.value}] {c.name}{extra}")
        print()

    # ----- phases -----

    def start_phase(self, p: PlayerState) -> None:
        p.cp = min(5, p.cp + 2)
        self._draw(p, 1)
        # reset attacks
        for z in self.zones.values():
            for u in z.units:
                if u.owner == p.pid:
                    u.attacked_this_turn = False

    def deploy_troop_from_hand(self, p: PlayerState, hand_index: int, target_zone: ZoneId) -> bool:
        if hand_index < 0 or hand_index >= len(p.hand):
            return False
        card = p.hand[hand_index]
        if not isinstance(card, TroopCard):
            return False
        z = self.zone(target_zone)
        if not z.has_space():
            return False

        unit = Unit(
            card=card,
            owner=p.pid,
            zone=target_zone,
            coh=card.stats.coh,
            ammo=card.stats.max_ammo,
        )
        z.units.append(unit)
        p.discard.append(card)
        p.hand.pop(hand_index)
        return True

    # ----- very simple demo loop -----

    def play_one_turn(self) -> None:
        p = self.player(self.active_pid)
        print(f"\n===== TURN {self.turn} — Player {p.pid} =====")
        self.start_phase(p)
        self.print_board()
        self.print_hand(p)

        # For MVP: allow 1 troop deploy to HQ or RESERVE only
        while True:
            choice = input("Type 'd' to deploy a troop, or 'end' to end turn: ").strip().lower()
            if choice == "end":
                break
            if choice == "d":
                idx = input("Which hand number? ").strip()
                z = input("Zone (HQ or RESERVE): ").strip().upper()
                if not idx.isdigit():
                    print("Not a number.")
                    continue
                if z not in ["HQ", "RESERVE"]:
                    print("Only HQ or RESERVE for now.")
                    continue
                ok = self.deploy_troop_from_hand(p, int(idx) - 1, ZoneId[z])
                print("Deployed!" if ok else "Failed to deploy.")
                self.print_board()
                self.print_hand(p)

        # swap player
        self.active_pid = self.other_pid(self.active_pid)
        if self.active_pid == 1:
            self.turn += 1

    def game_over(self) -> Optional[int]:
        if self.p1.morale <= 0:
            return 2
        if self.p2.morale <= 0:
            return 1
        return None


def main():
    print("Clash of Commands — Starter Prototype")
    print("This version only lets you DRAW and DEPLOY troops to HQ/RESERVE.\n")
    g = Game()
    while True:
        winner = g.game_over()
        if winner is not None:
            print(f"PLAYER {winner} WINS!")
            break
        g.play_one_turn()


if __name__ == "__main__":
    main()

