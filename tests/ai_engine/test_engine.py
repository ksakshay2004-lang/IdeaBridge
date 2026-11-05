import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from ai_engine import EvaluationEngine, LocalHashEmbedder, Retrieved, match_idea_to_profile, get_embedder, get_llm
from ai_engine.similarity import cosine, top_k
from ai_engine.schema import extract_json, clamp_score
from ai_engine.llm import LLMProvider

DATA = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "ai_engine", "data", "reference_projects.json")))
IDEA = {"title": "Spaced repetition flashcards for rural students",
        "short_description": "Offline-first flashcard app using spaced repetition to help rural students learn.",
        "problem": "Rural students lack reliable internet and tutoring so they struggle to memorise material before exams. " * 2,
        "solution": "A mobile app delivering flashcards with spaced repetition scheduling that works offline and syncs later.",
        "industry": "EdTech", "target_audience": "Rural secondary school students, teachers",
        "technologies": ["Mobile App"], "stage": "prototype", "business_potential": "Subscription for schools and NGO grants",
        "funding_needed": 50000}


def retrieved_for(emb, idea_text, k=6):
    q = emb.embed_one(idea_text)
    vecs = emb.embed([d["name"] + ". " + d["description"] for d in DATA])
    ranked = top_k(q, [(i, v) for i, v in enumerate(vecs)], k)
    return [Retrieved(id=DATA[i]["slug"], kind="reference", title=DATA[i]["name"], description=DATA[i]["description"],
                      similarity=s, url=DATA[i]["url"]) for i, s in ranked]


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.e = LocalHashEmbedder(384)

    def test_deterministic_normalised_dimension(self):
        a, b = self.e.embed_one("solar powered irrigation"), self.e.embed_one("solar powered irrigation")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 384)
        self.assertAlmostEqual(sum(x * x for x in a), 1.0, places=6)

    def test_similar_text_scores_higher_than_unrelated(self):
        q = self.e.embed_one("flashcards with spaced repetition for studying")
        close = self.e.embed_one("flashcard application using spaced repetition scheduling to memorise material")
        far = self.e.embed_one("freight forwarding customs shipment container logistics")
        self.assertGreater(cosine(q, close), cosine(q, far) + 0.2)

    def test_empty_text_is_safe(self):
        self.assertEqual(cosine(self.e.embed_one(""), self.e.embed_one("hello world")), 0.0)

    def test_factory_falls_back_to_local_without_key(self):
        self.assertEqual(get_embedder("openai", api_key="").name, "local-hash")
        self.assertIsNone(get_llm("anthropic", anthropic_key=""))

    def test_top_k_orders_best_first(self):
        res = top_k([1, 0], [("a", [0, 1]), ("b", [1, 0.1]), ("c", [0.5, 0.5])], 2)
        self.assertEqual([r[0] for r in res], ["b", "c"])

    def test_retrieval_finds_relevant_reference(self):
        emb = self.e
        text = IDEA["title"] + " " + IDEA["short_description"] + " " + IDEA["solution"]
        ids = [r.id for r in retrieved_for(emb, text, 3)]
        self.assertIn("anki", ids)


class DemoEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.emb = LocalHashEmbedder()
        self.engine = EvaluationEngine(None, self.emb.describe())
        text = " ".join([IDEA["title"], IDEA["short_description"], IDEA["problem"], IDEA["solution"]])
        self.retrieved = retrieved_for(self.emb, text, 6)
        self.report = self.engine.evaluate(IDEA, self.retrieved, {"reference_count": len(DATA), "platform_count": 0})

    def test_demo_is_clearly_labelled(self):
        m = self.report["meta"]
        self.assertEqual(m["mode"], "demo")
        self.assertIn("DEMO MODE", m["notice"])
        self.assertNotEqual(m["provider"], "anthropic")

    def test_report_has_all_sections_and_valid_scores(self):
        for k in ("idea_summary", "problem_statement", "proposed_solution", "similar_projects", "novelty_assessment",
                  "scores", "development_complexity", "target_users", "revenue_models", "strengths", "weaknesses",
                  "risks", "recommended_improvements", "overall_evaluation", "evidence"):
            self.assertIn(k, self.report)
        for k, v in self.report["scores"].items():
            self.assertTrue(0 <= v <= 100, k)

    def test_similar_projects_only_from_retrieved_and_pct_is_cosine(self):
        by_id = {r.id: r for r in self.retrieved}
        for s in self.report["similar_projects"]:
            self.assertIn(s["ref_id"], by_id)
            self.assertAlmostEqual(s["similarity_pct"], round(by_id[s["ref_id"]].similarity * 100, 1), places=1)
        for c in self.report["competitors"]:
            self.assertIn(c["ref_id"], by_id)

    def test_higher_similarity_lowers_differentiation(self):
        low = [Retrieved("x", "reference", "X", "d", 0.05)]
        high = [Retrieved("x", "reference", "X", "d", 0.85)]
        a = self.engine.evaluate(IDEA, low)["scores"]["innovation_differentiation"]
        b = self.engine.evaluate(IDEA, high)["scores"]["innovation_differentiation"]
        self.assertGreater(a, b + 30)

    def test_hidden_platform_idea_is_withheld(self):
        hidden = Retrieved("idea:7", "platform", "SECRET TITLE", "SECRET BODY", 0.6, visible=False)
        r = self.engine.evaluate(IDEA, [hidden])
        blob = json.dumps(r)
        self.assertNotIn("SECRET", blob)
        self.assertIn("details withheld", blob)


class FakeLLM(LLMProvider):
    name, model = "fake", "fake-1"

    def __init__(self, reply=None, fail=False):
        self.reply, self.fail, self.last_user = reply, fail, None

    def complete_json(self, system, user, max_tokens=3500):
        self.last_user = user
        if self.fail:
            raise RuntimeError("boom")
        return self.reply


class LLMPathTests(unittest.TestCase):
    def setUp(self):
        self.info = {"name": "openai", "kind": "semantic", "model": "m"}
        self.retrieved = [Retrieved("anki", "reference", "Anki", "Spaced repetition flashcards", 0.62, "https://apps.ankiweb.net"),
                          Retrieved("idea:9", "platform", "TOP SECRET", "TOP SECRET DESC", 0.5, visible=False)]

    def test_llm_output_is_sanitised_and_unknown_ids_ignored(self):
        reply = "```json\n" + json.dumps({
            "idea_summary": "S", "problem_statement": "P", "proposed_solution": "Sol",
            "similar_project_notes": [{"id": "anki", "key_differences": "offline"}, {"id": "invented", "key_differences": "x"}],
            "novelty_assessment": {"level": "HIGH", "rationale": "r"},
            "scores": {"technical_feasibility": 250, "market_opportunity": "abc", "innovation_differentiation": 99},
            "development_complexity": {"level": "weird", "rationale": ""},
            "target_users": ["a"], "revenue_models": ["b"], "competitor_ids": ["anki", "FakeCorp", "idea:9"],
            "strengths": ["s"], "weaknesses": ["w"], "risks": ["r"], "recommended_improvements": ["i"],
            "overall_evaluation": "ok"}) + "\n```"
        llm = FakeLLM(reply)
        rep = EvaluationEngine(llm, self.info).evaluate(IDEA, self.retrieved)
        self.assertEqual(rep["meta"]["mode"], "live_llm")
        self.assertEqual(rep["scores"]["technical_feasibility"], 100)
        self.assertEqual(rep["scores"]["market_opportunity"], 50)
        self.assertEqual(rep["novelty_assessment"]["level"], "high")
        self.assertEqual(rep["development_complexity"]["level"], "moderate")
        self.assertEqual([c["ref_id"] for c in rep["competitors"]], ["anki"])
        self.assertNotIn("invented", json.dumps(rep["similar_projects"]))
        self.assertEqual(rep["similar_projects"][0]["key_differences"], "offline")

    def test_private_content_never_sent_to_llm(self):
        llm = FakeLLM("{}")
        EvaluationEngine(llm, self.info).evaluate(IDEA, self.retrieved)
        self.assertNotIn("TOP SECRET", llm.last_user)

    def test_llm_failure_falls_back_to_labelled_demo(self):
        rep = EvaluationEngine(FakeLLM(fail=True), self.info).evaluate(IDEA, self.retrieved)
        self.assertEqual(rep["meta"]["mode"], "demo")
        self.assertIn("failed", rep["meta"]["notice"])
        self.assertIn("fallback_reason", rep["meta"])

    def test_garbage_llm_output_falls_back(self):
        rep = EvaluationEngine(FakeLLM("not json at all"), self.info).evaluate(IDEA, self.retrieved)
        self.assertEqual(rep["meta"]["mode"], "demo")

    def test_near_duplicate_caps_innovation_for_semantic_embedder(self):
        reply = json.dumps({"scores": {"technical_feasibility": 70, "market_opportunity": 70, "innovation_differentiation": 95}})
        near = [Retrieved("anki", "reference", "Anki", "d", 0.93)]
        rep = EvaluationEngine(FakeLLM(reply), self.info).evaluate(IDEA, near)
        self.assertLessEqual(rep["scores"]["innovation_differentiation"], 40)


class UtilTests(unittest.TestCase):
    def test_extract_json_and_clamp(self):
        self.assertEqual(extract_json('noise {"a": 1} tail'), {"a": 1})
        with self.assertRaises(ValueError):
            extract_json("nothing")
        self.assertEqual(clamp_score(-5), 0)
        self.assertEqual(clamp_score(None, 42), 42)


class MatchingTests(unittest.TestCase):
    PROFILE = {"industries": ["EdTech"], "technologies": ["Mobile App", "AI"], "interests": "learning flashcards schools",
               "preferred_stages": ["prototype", "mvp"], "target_markets": ["students"], "investment_min": 10000,
               "investment_max": 100000}

    def test_strong_match_scores_high_with_reasons(self):
        m = match_idea_to_profile(IDEA, self.PROFILE)
        self.assertGreaterEqual(m["score"], 85)
        self.assertTrue(m["reasons"])
        self.assertEqual(sum(p["max"] for p in m["breakdown"].values()), 100)

    def test_mismatch_scores_low(self):
        other = dict(self.PROFILE, industries=["FinTech"], technologies=["Blockchain"], preferred_stages=["launched"],
                     target_markets=["banks"], investment_min=5_000_000, investment_max=9_000_000, interests="payments")
        self.assertLess(match_idea_to_profile(IDEA, other)["score"], 25)

    def test_empty_profile_is_neutral_not_crashing(self):
        m = match_idea_to_profile(IDEA, {})
        self.assertTrue(0 <= m["score"] <= 100)


if __name__ == "__main__":
    unittest.main()
