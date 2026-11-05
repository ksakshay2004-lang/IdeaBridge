import json
import os

import numpy as np
import pytest

from conftest import IDEA

pytest.importorskip("sqlalchemy")


def test_reference_dataset_seeded_with_embeddings(client):
    from sqlalchemy import func, select
    from app.database import SessionLocal
    from app.models import ReferenceProject
    data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "ai_engine", "data", "reference_projects.json")))
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ReferenceProject)) == len(data)
        row = db.scalar(select(ReferenceProject).limit(1))
        assert isinstance(row.embedding, list) and len(row.embedding) == 384 and row.embedding_model


def test_unique_constraints_and_cascades(client, signup, make_idea):
    from sqlalchemy import select, func
    from sqlalchemy.exc import IntegrityError
    from app.database import SessionLocal
    from app.models import Evaluation, Idea, SavedIdea, User
    cre, ent = signup("creator"), signup("entrepreneur")
    iid = make_idea(cre)["id"]
    with SessionLocal() as db:
        db.add_all([SavedIdea(user_id=ent["user"]["id"], idea_id=iid), SavedIdea(user_id=ent["user"]["id"], idea_id=iid)])
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.add(User(email=cre["email"], password_hash="x", full_name="Dup", role="creator"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.idea_id == iid)) == 1
        db.delete(db.get(User, cre["user"]["id"]))
        db.commit()
        assert db.get(Idea, iid) is None
        assert db.scalar(select(func.count()).select_from(Evaluation).where(Evaluation.idea_id == iid)) == 0


def test_idea_embedding_is_stored_after_evaluation(client, signup, make_idea):
    from app.database import SessionLocal
    from app.models import Idea
    iid = make_idea(signup("creator"))["id"]
    with SessionLocal() as db:
        idea = db.get(Idea, iid)
        assert len(idea.embedding) == 384 and abs(sum(x * x for x in idea.embedding) - 1) < 1e-6


def test_reported_similarity_equals_real_cosine(client, signup, make_idea):
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import Evaluation, Idea, ReferenceProject, SimilarityResult
    iid = make_idea(signup("creator"))["id"]
    with SessionLocal() as db:
        idea = db.get(Idea, iid)
        ev = db.scalar(select(Evaluation).where(Evaluation.idea_id == iid))
        rows = db.scalars(select(SimilarityResult).where(SimilarityResult.evaluation_id == ev.id,
                                                         SimilarityResult.source_type == "reference")).all()
        assert rows
        for r in rows:
            ref = db.scalar(select(ReferenceProject).where(ReferenceProject.slug == r.source_ref))
            a, b = np.array(idea.embedding), np.array(ref.embedding)
            cos = float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
            assert r.similarity == pytest.approx(round(max(cos, 0) * 100, 1), abs=0.11)
        assert all(r.url is None or r.url.startswith("http") for r in rows)
        assert ev.report["similar_projects"][0]["ref_id"] in {x.source_ref for x in rows}


def test_report_is_gated_for_anonymous_and_retrieves_relevant_reference(client, signup, make_idea):
    cre = signup("creator")
    iid = make_idea(cre)["id"]
    assert client.get(f"/api/ideas/{iid}/evaluation").status_code == 403  # anonymous
    rep = client.get(f"/api/ideas/{iid}/evaluation", headers=cre["h"]).json()["current"]["report"]
    refs = [s["ref_id"] for s in rep["similar_projects"] if s["kind"] == "reference"]
    assert "anki" in refs  # flashcards / spaced repetition idea should retrieve Anki


def test_other_users_ideas_are_never_leaked_in_reports(client, signup, make_idea):
    unique = {"title": "Zyxwv quantum lattice glacier modelling", "short_description": "Zyxwv glacier lattice modelling toolkit for quantum climate researchers.",
              "problem": "Zyxwv glacier lattice researchers lack toolkits for modelling quantum climate effects accurately.",
              "solution": "A Zyxwv toolkit combining glacier lattice simulation with quantum climate modelling workflows.",
              "industry": "CleanTech", "technologies": ["Cloud"]}
    a, b = signup("creator"), signup("creator")
    make_idea(a, visibility="private", **{**unique, "title": "Private marker Zyxwv glacier lattice secret"})
    make_idea(a, visibility="restricted", **{**unique, "title": "Restricted marker Zyxwv glacier lattice secret"})
    pub = make_idea(a, visibility="public", **{**unique, "title": "Public marker Zyxwv glacier lattice open"})
    mine = make_idea(b, visibility="public", **unique)
    rep = client.get(f"/api/ideas/{mine['id']}/evaluation", headers=b["h"]).json()["current"]["report"]
    blob = json.dumps(rep)
    titles = [s["title"] for s in rep["similar_projects"] if s["kind"] == "platform"]
    assert pub["title"] in titles                       # public neighbour may be named
    assert any("details withheld" in t for t in titles)  # restricted neighbour is anonymised
    assert "Restricted marker" not in blob              # ...and its title never leaks
    assert "Private marker" not in blob                 # private ideas are never compared or shown


def test_llm_failure_falls_back_to_labelled_demo(client, signup, make_idea, monkeypatch):
    from ai_engine import EvaluationEngine
    from ai_engine.llm import LLMProvider
    from app.services import evaluation, vectors

    class Broken(LLMProvider):
        name, model = "fake", "fake"

        def complete_json(self, *a, **k):
            raise RuntimeError("provider down")

    monkeypatch.setattr(evaluation, "build_engine", lambda force_demo=False: EvaluationEngine(Broken(), vectors.embedder().describe()))
    cre = signup("creator")
    idea = make_idea(cre)
    ev = client.get(f"/api/ideas/{idea['id']}/evaluation", headers=cre["h"]).json()["current"]
    assert ev["mode"] == "demo" and "failed" in ev["report"]["meta"]["notice"]


def test_live_llm_report_is_labelled_live(client, signup, make_idea, monkeypatch):
    from ai_engine import EvaluationEngine
    from ai_engine.llm import LLMProvider
    from app.services import evaluation, vectors

    class Good(LLMProvider):
        name, model = "fake-live", "fake-1"

        def complete_json(self, *a, **k):
            return json.dumps({"idea_summary": "ok", "scores": {"technical_feasibility": 71, "market_opportunity": 64,
                                                                  "innovation_differentiation": 58}})

    monkeypatch.setattr(evaluation, "build_engine", lambda force_demo=False: EvaluationEngine(Good(), vectors.embedder().describe()))
    cre = signup("creator")
    idea = make_idea(cre)
    ev = client.get(f"/api/ideas/{idea['id']}/evaluation", headers=cre["h"]).json()["current"]
    assert ev["mode"] == "live_llm" and ev["provider"] == "fake-live" and ev["report"]["meta"]["notice"] is None


def test_system_status_reports_demo_mode(client):
    s = client.get("/api/system/status").json()
    assert s["evaluation_mode"] == "demo" and "DEMO MODE" in s["demo_notice"] and s["embedding"]["kind"] == "lexical"
    assert "key" not in json.dumps(s).lower()


def test_re_evaluate_conflict_and_versions(client, signup, make_idea):
    cre = signup("creator")
    iid = make_idea(cre)["id"]
    r = client.post(f"/api/ideas/{iid}/evaluate", headers=cre["h"])
    assert r.status_code == 202 and r.json()["version"] == 2
    ev = client.get(f"/api/ideas/{iid}/evaluation", headers=cre["h"]).json()["current"]
    assert ev["version"] == 2 and ev["status"] == "completed"
