# risk_game.py
# Core logic for the Risk board game

from enum import Enum
import random

class Phase(Enum):
    REINFORCEMENT = 1
    ATTACK = 2
    FORTIFY = 3

class Territory:
    def __init__(self, name, neighbors):
        self.name = name
        self.neighbors = neighbors  # List of territory names
        self.owner = None
        self.armies = 0

class Player:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.territories = set()

class RiskGame:
    def __init__(self, territory_map, player_names):
        self.territories = {name: Territory(name, neighbors) for name, neighbors in territory_map.items()}
        colors = ["red", "blue", "green", "yellow", "purple", "orange"]
        self.players = [Player(name, colors[i % len(colors)]) for i, name in enumerate(player_names)]
        self.current_player_idx = 0
        self.phase = Phase.REINFORCEMENT
        self.assign_initial_territories()

    def assign_initial_territories(self):
        territory_names = list(self.territories.keys())
        random.shuffle(territory_names)
        for i, tname in enumerate(territory_names):
            player = self.players[i % len(self.players)]
            self.territories[tname].owner = player
            self.territories[tname].armies = 1
            player.territories.add(tname)

    # Add more methods for reinforcement, attack, fortify, etc.
