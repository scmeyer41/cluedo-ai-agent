"""Mansion graph and movement utilities for the Cluedo game."""

from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Dict, List, Tuple


MANSION_GRAPH: Dict[str, Dict[str, int]] = {
    "Study": {"Library": 3, "Hall": 3, "Kitchen": 0},
    "Library": {"Study": 3, "Billiard Room": 3},
    "Billiard Room": {"Library": 3, "Conservatory": 3},
    "Conservatory": {"Billiard Room": 3, "Ballroom": 4, "Lounge": 0},
    "Ballroom": {"Conservatory": 4, "Kitchen": 4},
    "Kitchen": {"Ballroom": 4, "Dining Room": 3, "Study": 0},
    "Dining Room": {"Kitchen": 3, "Lounge": 3},
    "Lounge": {"Dining Room": 3, "Hall": 4, "Conservatory": 0},
    "Hall": {"Study": 3, "Lounge": 4},
}

ROOMS = list(MANSION_GRAPH.keys())


@dataclass(frozen=True)
class Route:
    """A legal route through the mansion graph."""

    rooms: Tuple[str, ...]
    cost: int

    @property
    def destination(self) -> str:
        return self.rooms[-1]

    def display(self) -> str:
        return " -> ".join(self.rooms) + f" (cost {self.cost})"


def neighbors(room: str) -> Dict[str, int]:
    """Return adjacent rooms and movement costs for a room."""
    return MANSION_GRAPH.get(room, {})


def secret_passages(room: str) -> List[str]:
    """Return all zero-cost destinations from a room."""
    return [
        destination
        for destination, cost in neighbors(room).items()
        if cost == 0
    ]


def find_routes(start: str, maximum_cost: int) -> List[Route]:
    """Return affordable one-edge moves to adjacent rooms."""
    routes: List[Route] = []

    for destination, edge_cost in neighbors(start).items():
        if edge_cost <= maximum_cost:
            routes.append(Route((start, destination), edge_cost))

    return sorted(routes, key=lambda route: (route.cost, route.destination))


def direct_secret_route(start: str, destination: str) -> Route | None:
    """Return a zero-cost direct secret-passage route when one exists."""
    if neighbors(start).get(destination) == 0:
        return Route((start, destination), 0)
    return None


def shortest_route(start: str, destination: str) -> Route | None:
    """Use Dijkstra's algorithm to find the least-cost route between rooms."""
    queue: List[Tuple[int, str, Tuple[str, ...]]] = [(0, start, (start,))]
    best = {start: 0}
    while queue:
        cost, room, path = heapq.heappop(queue)
        if room == destination:
            return Route(path, cost)
        if cost > best.get(room, cost):
            continue
        for neighbor, edge_cost in neighbors(room).items():
            new_cost = cost + edge_cost
            if new_cost < best.get(neighbor, 10**9):
                best[neighbor] = new_cost
                heapq.heappush(queue, (new_cost, neighbor, path + (neighbor,)))
    return None


def distance(start: str, destination: str) -> int:
    route = shortest_route(start, destination)
    return route.cost if route is not None else 10**9
