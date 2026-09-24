"""Independent dictionary-level replay for joint contradiction certificates.

This module deliberately does not import ``src.joint`` or the producer.  It
checks retained source anchors, proof trees, closure, and exact optimality for
the bounded public cases by enumerating origin subsets.
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Iterable


class ReplayError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def _safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    require(path.is_relative_to(root.resolve()), "source path escapes artifact root")
    require(path.is_file(), f"missing retained source: {relative}")
    return path


def _anchor(root: Path, path: str, anchor: str) -> None:
    require(type(path) is str and type(anchor) is str and anchor, "malformed source anchor")
    text = _safe_path(root, path).read_text()
    require(text.count(anchor) == 1, f"source anchor must occur exactly once: {path}")


def validate_problem(problem: dict, root: Path) -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    require(problem.get("negative") == "not:" + problem.get("positive", ""), "target pair mismatch")
    origins = {}
    for origin in problem.get("origins", []):
        identifier = origin.get("id")
        require(type(identifier) is str and identifier and identifier not in origins, "duplicate/malformed origin")
        require(type(origin.get("weight")) is int and origin["weight"] >= 0, "invalid origin weight")
        kind = origin.get("kind")
        require(kind in {"code", "change", "bridge", "seed", "context"}, "invalid origin kind")
        if kind == "code":
            _anchor(root, origin.get("path"), origin.get("anchor"))
        elif kind == "change":
            meta = origin.get("metadata", {})
            for key in ("before_path", "after_path", "before_anchor", "after_anchor", "before_tag", "after_tag"):
                require(type(meta.get(key)) is str and meta[key], f"missing change metadata: {key}")
            _anchor(root, meta["before_path"], meta["before_anchor"])
            _anchor(root, meta["after_path"], meta["after_anchor"])
            require(meta["before_anchor"] != meta["after_anchor"], "change endpoints are identical")
        elif kind == "bridge":
            require(bool(origin.get("metadata", {}).get("assumption")), "bridge assumption not stated")
        origins[identifier] = origin
    require(origins, "problem has no origins")

    facts = {}
    for fact in problem.get("facts", []):
        name = fact.get("name")
        require(type(name) is str and name and name not in facts, "duplicate/malformed fact")
        ids = fact.get("origins")
        require(type(ids) is list and len(ids) == len(set(ids)) and set(ids) <= origins.keys(), "invalid fact origins")
        require(type(fact.get("literal")) is str and fact["literal"], "invalid fact literal")
        facts[name] = fact

    rules = {}
    for rule in problem.get("rules", []):
        name = rule.get("name")
        require(type(name) is str and name and name not in rules and name not in facts, "duplicate/malformed rule")
        body = rule.get("body")
        require(type(body) is list and len(body) == len(set(body)), "invalid rule body")
        require(type(rule.get("head")) is str and rule["head"], "invalid rule head")
        rules[name] = rule
    return origins, facts, rules


def replay_proof(node: dict, facts: dict[str, dict], rules: dict[str, dict]) -> tuple[str, frozenset[str]]:
    require(type(node) is dict, "proof node must be an object")
    step = node.get("step")
    literal = node.get("literal")
    support_list = node.get("support")
    premises = node.get("premises")
    require(type(literal) is str and type(support_list) is list and type(premises) is list, "malformed proof node")
    support = frozenset(support_list)
    require(len(support) == len(support_list), "duplicate support entry")
    if step in facts:
        fact = facts[step]
        require(not premises, "fact node has premises")
        require(literal == fact["literal"], "fact literal mismatch")
        require(support == frozenset(fact["origins"]), "fact support mismatch")
    elif step in rules:
        rule = rules[step]
        require(literal == rule["head"], "rule head mismatch")
        require(len(premises) == len(rule["body"]), "rule arity mismatch")
        replayed = [replay_proof(p, facts, rules) for p in premises]
        require([x[0] for x in replayed] == rule["body"], "rule premise order/literals mismatch")
        union = frozenset().union(*(x[1] for x in replayed)) if replayed else frozenset()
        require(support == union, "rule support union mismatch")
    else:
        raise ReplayError(f"unknown proof step: {step}")
    return literal, support


def closure(problem: dict, selected: Iterable[str]) -> frozenset[str]:
    selected = frozenset(selected)
    known = {
        fact["literal"] for fact in problem["facts"]
        if set(fact["origins"]) <= selected
    }
    while True:
        add = {
            rule["head"] for rule in problem["rules"]
            if set(rule["body"]) <= known
        } - known
        if not add:
            return frozenset(known)
        known |= add


def contradictory(problem: dict, selected: Iterable[str]) -> bool:
    known = closure(problem, selected)
    return problem["positive"] in known and problem["negative"] in known


def cost(origins: dict[str, dict], selected: Iterable[str]) -> int:
    ids = frozenset(selected)
    require(ids <= origins.keys(), "selection contains unknown origin")
    return sum(origins[x]["weight"] for x in ids)


def exact_oracle(problem: dict, origins: dict[str, dict], limit: int = 16) -> tuple[int, frozenset[str]] | None:
    ids = tuple(sorted(origins))
    require(len(ids) <= limit, "independent oracle bound exceeded")
    best = None
    for size in range(len(ids) + 1):
        for subset in combinations(ids, size):
            if contradictory(problem, subset):
                key = (cost(origins, subset), len(subset), subset)
                if best is None or key < best[0]:
                    best = (key, frozenset(subset))
    return None if best is None else (best[0][0], best[1])


def replay_certificate(document: dict, root: Path) -> dict:
    require(document.get("schema") == "joint-contradiction-certificate-v1", "certificate schema mismatch")
    problem = document.get("problem")
    solution = document.get("solution")
    require(type(problem) is dict and type(solution) is dict, "certificate sections missing")
    origins, facts, rules = validate_problem(problem, root)
    oracle = exact_oracle(problem, origins)
    status = solution.get("status")
    if status == "no-contradiction-certificate":
        require(oracle is None, "producer reported no certificate but oracle found one")
        return {"case": problem["name"], "status": status, "oracle": "none"}
    require(status == "certificate", "unknown solution status")
    selected_list = solution.get("selected")
    require(type(selected_list) is list and len(selected_list) == len(set(selected_list)), "malformed selection")
    selected = frozenset(selected_list)
    require(selected <= origins.keys(), "unknown selected origin")
    p_lit, p_support = replay_proof(solution.get("positive_proof"), facts, rules)
    n_lit, n_support = replay_proof(solution.get("negative_proof"), facts, rules)
    require(p_lit == problem["positive"] and n_lit == problem["negative"], "proof conclusions mismatch")
    require(selected == p_support | n_support, "selection is not proof-support union")
    require(contradictory(problem, selected), "selected origins do not replay contradiction")
    reported_cost = solution.get("cost")
    require(type(reported_cost) is int and reported_cost == cost(origins, selected), "reported cost mismatch")
    require(oracle is not None and oracle[0] == reported_cost, "certificate is not globally minimum")
    reported_oracle = document.get("oracle_selected")
    require(type(reported_oracle) is list and cost(origins, reported_oracle) == oracle[0], "producer oracle witness mismatch")
    return {
        "case": problem["name"],
        "status": status,
        "cost": reported_cost,
        "selected_origins": len(selected),
        "oracle_cost": oracle[0],
    }
