import random
from typing import Sequence, List, Optional

from shapely import unary_union
from shapely.geometry.base import BaseGeometry


def _positive_area(g: BaseGeometry, tol: float):
    return not g.is_empty and g.area > tol


def union_all(geoms: Sequence[BaseGeometry]) -> BaseGeometry:
    return unary_union(list(geoms))


def mandatory_indices(geoms: Sequence[BaseGeometry], *, tol: float = 1e-9) -> List[int]:
    n = len(geoms)
    out: List[int] = []
    for i in range(n):
        g = geoms[i]
        if g.is_empty:
            continue
        others = [geoms[j] for j in range(n) if j != i]
        u = union_all(others) if others else None
        exclusive = g if u is None or u.is_empty else g.difference(u)
        if _positive_area(exclusive, tol):
            out.append(i)
    return out


def _covers(u_rest: BaseGeometry, universe: BaseGeometry, tol: float) -> bool:
    if u_rest.is_empty:
        return universe.is_empty or universe.area <= tol
    hole = universe.difference(u_rest)
    return hole.is_empty or hole.area <= tol


def reverse_prune(
        geoms: Sequence[BaseGeometry],
        chosen: List[int],
        universe: BaseGeometry,
        mandatory_indices: Optional[List[int]] = None,
        *,
        tol: float = 1e-9,
        rng: Optional[random.Random] = None
) -> List[int]:
    if rng is None:
        rng = random.Random(0)

    mandatory_set = set(mandatory_indices) if mandatory_indices else set()
    mandatory_union = union_all([geoms[i] for i in mandatory_set]) if mandatory_set else None

    s = list(chosen)
    changed = True
    while changed:
        changed = False
        order = s[:]
        rng.shuffle(order)
        for i in order:
            if i not in s or len(s) <= 1:
                continue
            if i in mandatory_set:
                continue
            rest_idx = [j for j in s if j != i]
            if mandatory_union:
                u_rest = unary_union([mandatory_union] + [geoms[j] for j in rest_idx])
            else:
                u_rest = union_all([geoms[j] for j in rest_idx])
            if _covers(u_rest, universe, tol):
                s.remove(i)
                changed = True
    return s


def greedy_sweep_cover(
        geoms: Sequence[BaseGeometry],
        *,
        tol: float = 1e-9,
        multi_start: int = 1,
        seed: int = 0,
        mandatory_polygons: Optional[Sequence[BaseGeometry]] = None
) -> List[int]:
    original_n = len(geoms)
    mandatory_polygons_indices: List[int] = []
    all_geoms_with_mandatory = list(geoms)
    if mandatory_polygons:
        for mp in mandatory_polygons:
            if not mp.is_empty:
                all_geoms_with_mandatory.append(mp)
                mandatory_polygons_indices.append(len(all_geoms_with_mandatory) - 1)

    n = len(all_geoms_with_mandatory)
    if n == 0:
        return []

    universe = union_all(all_geoms_with_mandatory)

    if not _positive_area(universe, tol=tol):
        return []

    mandatory = mandatory_indices(geoms, tol=tol)
    mandatory_set = set(mandatory) | set(mandatory_polygons_indices)

    geoms = all_geoms_with_mandatory

    best: Optional[List[int]] = None

    for t in range(max(1, multi_start)):
        rng = random.Random(seed + t)
        chosen: List[int] = list(dict.fromkeys(mandatory)) + mandatory_polygons_indices
        uncovered = universe
        if chosen:
            uncovered = universe.difference(union_all([geoms[i] for i in chosen]))

        candidates = [i for i in range(n) if i not in mandatory_set]

        iterations = 0
        while _positive_area(uncovered, tol):
            iterations += 1
            best_i: Optional[int] = None
            best_gain = -1.0
            ties: List[int] = []
            for i in candidates:
                inter = geoms[i].intersection(uncovered)
                gain = inter.area if not inter.is_empty else 0.0
                if gain > best_gain + tol:
                    best_gain = gain
                    best_i = i
                    ties = [i]
                elif abs(gain - best_gain) <= tol < gain:
                    ties.append(i)
            if best_i is None or best_gain <= tol:
                if uncovered.area <= 1e-6:
                    break
                raise RuntimeError(
                    "Greedy stalled: union of sweeps does not cover the full union, or geomtry/tolerance issue"
                )
            pick = rng.choice(ties)
            chosen.append(pick)
            candidates.remove(pick)
            uncovered = uncovered.difference(geoms[pick])
        chosen = reverse_prune(
            geoms, chosen, universe, mandatory_indices=mandatory_polygons_indices,
            tol=tol, rng=rng
        )

        if best is None or len(chosen) < len(best):
            best = chosen

    assert best is not None
    result = [i for i in best if i < original_n]
    return result
