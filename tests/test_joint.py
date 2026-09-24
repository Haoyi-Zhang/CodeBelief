import copy
import json
import random
import tempfile
import unittest
from pathlib import Path

from src.joint import (
    Fact, Origin, Problem, Rule, brute_force_optimum, closure, contradictory,
    derive_antichains, greedy_delete, independent_sides, is_inclusion_minimal,
    make_deletion_gap, make_tight_two_approx, negate, problem_to_dict,
    solution_to_dict, solve_exact, support_cost,
)
from src.joint_benchmark import HOSTS, public_problem, random_problem
from src.joint_replay import ReplayError, replay_certificate

ROOT = Path(__file__).resolve().parents[1]


class JointModelTests(unittest.TestCase):
    def test_strong_negation_is_involution(self):
        for literal in ("p", "policy:x", "not:q"):
            self.assertEqual(negate(negate(literal)), literal)

    def test_fact_only_contradiction(self):
        problem = Problem("basic", (Origin("a", "seed"), Origin("b", "seed")),
                          (Fact("fa", "p", ("a",)), Fact("fb", "not:p", ("b",))), (), "p", "not:p")
        answer = solve_exact(problem)
        self.assertEqual(answer.cost, 2)
        self.assertEqual(answer.selected, frozenset({"a", "b"}))

    def test_shared_origin_is_counted_once(self):
        problem = Problem("shared", (Origin("s", "seed", 3),),
                          (Fact("fa", "p", ("s",)), Fact("fb", "not:p", ("s",))), (), "p", "not:p")
        self.assertEqual(solve_exact(problem).cost, 3)

    def test_weighted_minimum_not_cardinality_minimum(self):
        origins=(Origin("heavy", "seed", 9), Origin("x", "seed", 1), Origin("y", "seed", 1))
        facts=(Fact("p1","p",("heavy",)),Fact("n1","not:p",("heavy",)),
               Fact("p2","p",("x","y")),Fact("n2","not:p",("x","y")))
        problem=Problem("weights",origins,facts,(),"p","not:p")
        self.assertEqual(solve_exact(problem).selected,frozenset({"x","y"}))

    def test_rule_chain(self):
        problem=Problem("chain",(Origin("a","seed"),Origin("b","seed")),
            (Fact("fa","a",("a",)),Fact("fb","b",("b",))),
            (Rule("a1",("a",),"a2"),Rule("a2",("a2",),"p"),Rule("b1",("b",),"not:p")),"p","not:p")
        answer=solve_exact(problem)
        self.assertEqual(answer.positive_proof.depth,3)
        self.assertTrue(contradictory(problem,answer.selected))

    def test_unproductive_cycle_terminates(self):
        problem=Problem("cycle",(Origin("a","seed"),),(Fact("f","a",("a",)),),
            (Rule("ab",("a",),"b"),Rule("ba",("b",),"a")),"p","not:p")
        frontiers,iterations=derive_antichains(problem)
        self.assertIn("b",frontiers)
        self.assertLess(iterations,5)
        self.assertIsNone(solve_exact(problem))

    def test_oracle_agrees_on_random_weighted_instances(self):
        rng=random.Random(991)
        for n in range(4,10):
            for i in range(12):
                problem=random_problem(rng,i,n)
                exact=solve_exact(problem); oracle=brute_force_optimum(problem)
                self.assertEqual(exact is None,oracle is None)
                if exact is not None:self.assertEqual(exact.cost,support_cost(problem,oracle))

    def test_independent_side_bound(self):
        for k in (2,3,8,32):
            problem=make_tight_two_approx(k); exact=solve_exact(problem); approx=independent_sides(problem)
            self.assertLessEqual(approx.cost,2*exact.cost)

    def test_two_approximation_family_is_tight(self):
        problem=make_tight_two_approx(64)
        exact=solve_exact(problem); approx=independent_sides(problem)
        self.assertEqual((exact.cost,approx.cost),(65,128))
        self.assertGreater(approx.cost/exact.cost,1.96)

    def test_deletion_returns_inclusion_minimal_but_not_minimum(self):
        problem,order=make_deletion_gap(20)
        chosen=greedy_delete(problem,order)
        self.assertTrue(is_inclusion_minimal(problem,chosen))
        self.assertEqual(support_cost(problem,chosen),20)
        self.assertEqual(solve_exact(problem).cost,1)

    def test_closure_rejects_unknown_origin(self):
        problem=make_tight_two_approx(2)
        with self.assertRaises(ValueError):closure(problem,{"unknown"})

    def test_problem_rejects_nonopposite_targets(self):
        with self.assertRaises(ValueError):
            Problem("bad",(),(),(),"p","q")


class PublicHostTests(unittest.TestCase):
    def test_all_declared_anchors_exist_once(self):
        for host in HOSTS.values():
            for which in ("before","after"):
                text=(ROOT/host[f"{which}_path"]).read_text()
                self.assertEqual(text.count(host[f"{which}_feature"]),1)
                self.assertEqual(text.count(host[f"{which}_context"]),1)
            self.assertEqual((ROOT/host["after_path"]).read_text().count(host["shared_context"]),1)

    def test_positive_public_cases_have_certificates(self):
        for host in HOSTS:
            for profile in ("unit","history-heavy","code-heavy"):
                for variant in ("direct","chain","choice"):
                    self.assertIsNotNone(solve_exact(public_problem(host,variant,profile)))

    def test_negative_controls_have_no_certificate(self):
        for host in HOSTS:
            for profile in ("unit","history-heavy","code-heavy"):
                for variant in ("no-bridge-control","single-side-control"):
                    self.assertIsNone(solve_exact(public_problem(host,variant,profile)))

    def test_choice_exercises_union_awareness(self):
        for host in HOSTS:
            problem=public_problem(host,"choice","unit")
            self.assertEqual((solve_exact(problem).cost,independent_sides(problem).cost),(3,4))

    def _document(self):
        problem=public_problem("cjson","choice","unit"); solution=solve_exact(problem)
        return {"schema":"joint-contradiction-certificate-v1","problem":problem_to_dict(problem),
                "solution":solution_to_dict(problem,solution,algorithm="exact-antichain"),
                "oracle_selected":sorted(brute_force_optimum(problem))}

    def test_independent_replay_accepts_valid_certificate(self):
        result=replay_certificate(self._document(),ROOT)
        self.assertEqual(result["status"],"certificate")
        self.assertEqual(result["cost"],3)

    def test_replay_rejects_mutated_anchor(self):
        document=self._document(); document["problem"]["origins"][0]["anchor"]="not in source"
        with self.assertRaises(ReplayError):replay_certificate(document,ROOT)

    def test_replay_rejects_path_escape(self):
        document=self._document(); document["problem"]["origins"][0]["path"]="../outside.c"
        with self.assertRaises(ReplayError):replay_certificate(document,ROOT)

    def test_replay_rejects_cost_tampering(self):
        document=self._document(); document["solution"]["cost"]+=1
        with self.assertRaises(ReplayError):replay_certificate(document,ROOT)

    def test_replay_rejects_proof_tampering(self):
        document=self._document(); document["solution"]["positive_proof"]["literal"]="wrong"
        with self.assertRaises(ReplayError):replay_certificate(document,ROOT)

    def test_replay_accepts_negative_control(self):
        problem=public_problem("mjson","no-bridge-control","unit")
        document={"schema":"joint-contradiction-certificate-v1","problem":problem_to_dict(problem),
                  "solution":solution_to_dict(problem,None,algorithm="exact-antichain"),"oracle_selected":None}
        result=replay_certificate(document,ROOT)
        self.assertEqual(result["oracle"],"none")


if __name__ == "__main__":
    unittest.main()
