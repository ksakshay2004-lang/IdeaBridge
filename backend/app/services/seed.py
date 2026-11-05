"""Bootstrap data: categories, curated reference projects, optional admin and DEMO sample data."""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import (Category, CollaborationRequest, CreatorProfile, EntrepreneurProfile, Idea, Message, User)
from ..security import hash_password
from . import vectors
from .evaluation import create_evaluation, run_evaluation

log = logging.getLogger("ideabridge.seed")

INDUSTRIES = ["Healthcare", "EdTech", "FinTech", "AgriTech", "CleanTech", "AI / Machine Learning", "E-commerce",
              "Logistics", "Cybersecurity", "IoT", "Social Impact", "Entertainment", "Real Estate", "Other"]
TECHNOLOGIES = ["Web App", "Mobile App", "AI / ML", "Blockchain", "IoT", "Cloud", "Data Analytics", "AR/VR",
                "Robotics", "Biotech", "Hardware", "API / SaaS", "Computer Vision", "NLP"]
DEMO_PASSWORD = "Demo@12345"  # development/demo accounts only


def ensure_categories(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Category)):
        return
    db.add_all([Category(name=n, kind="industry") for n in INDUSTRIES] +
               [Category(name=n, kind="technology") for n in TECHNOLOGIES])
    db.commit()


def ensure_admin(db: Session) -> None:
    s = get_settings()
    if not (s.admin_email and s.admin_password):
        return
    if db.scalar(select(User.id).where(func.lower(User.email) == s.admin_email.lower())):
        return
    db.add(User(email=s.admin_email.lower(), password_hash=hash_password(s.admin_password), full_name="Administrator",
                role="admin", is_verified=True))
    db.commit()
    log.info("Admin account %s created", s.admin_email)


def _user(db, email, name, role, verified=False):
    u = User(email=email, password_hash=hash_password(DEMO_PASSWORD), full_name=name, role=role, is_verified=verified)
    db.add(u)
    db.flush()
    return u


def seed_demo(db: Session) -> None:
    """Sample content for demos. Clearly fictional; evaluations are produced by the local DEMO engine."""
    if db.scalar(select(func.count()).select_from(User)):
        return
    admin = _user(db, "admin@ideabridge.demo", "Demo Admin", "admin", True)
    maya = _user(db, "maya@ideabridge.demo", "Maya Thomas", "creator")
    arjun = _user(db, "arjun@ideabridge.demo", "Arjun Nair", "creator")
    lena = _user(db, "lena@ideabridge.demo", "Lena Fischer", "creator")
    ravi = _user(db, "ravi@ideabridge.demo", "Ravi Menon", "entrepreneur", True)
    sofia = _user(db, "sofia@ideabridge.demo", "Sofia Alvarez", "entrepreneur", True)
    _user(db, "omar@ideabridge.demo", "Omar Haddad", "entrepreneur", False)
    note = "Demo account with fictional sample data."
    for u, head, org in ((maya, "Final-year CS student", "Sample University"), (arjun, "Agronomy researcher", "Sample Institute"),
                         (lena, "Product designer", "Independent")):
        db.add(CreatorProfile(user_id=u.id, headline=head, organization=org, bio=note, skills=["research", "design"]))
    db.add(EntrepreneurProfile(user_id=ravi.id, company_name="Northwind Ventures (sample)", company_type="investor", bio=note,
                               industries=["EdTech", "AI / Machine Learning"], technologies=["Mobile App", "AI / ML"],
                               interests="learning tools, adaptive education, student productivity, offline access",
                               preferred_stages=["prototype", "mvp"], target_markets=["students", "schools"],
                               investment_min=20000, investment_max=250000))
    db.add(EntrepreneurProfile(user_id=sofia.id, company_name="GreenLeaf Labs (sample)", company_type="startup", bio=note,
                               industries=["AgriTech", "CleanTech"], technologies=["Computer Vision", "IoT"],
                               interests="crop health monitoring, smallholder farmers, sustainable agriculture",
                               preferred_stages=["concept", "research", "prototype"], target_markets=["farmers"],
                               investment_min=10000, investment_max=100000))
    db.add(EntrepreneurProfile(user_id=db.scalar(select(User.id).where(User.email == "omar@ideabridge.demo")),
                               company_name="Sample Corp (unverified)", company_type="corporate", bio=note,
                               industries=["Logistics"], technologies=["IoT"], interests="warehouse automation"))
    db.flush()
    ideas = [
        (maya, "Offline Spaced-Repetition Flashcards for Rural Schools", "A mobile app that lets rural students study with spaced-repetition flashcards fully offline and syncs progress when connectivity returns.",
         "Students in low-connectivity regions cannot rely on streaming video or cloud study tools, so exam revision is inconsistent and teachers have no visibility into who is struggling.",
         "An offline-first mobile app that schedules flashcards with a spaced-repetition algorithm, lets teachers distribute card decks over Bluetooth or SD cards, and syncs aggregate progress to a teacher dashboard when a connection is available.",
         "EdTech", "Rural secondary school students and their teachers", ["Mobile App", "Data Analytics"], "prototype", "public", 60000,
         "Improves exam preparation and gives teachers data on learning gaps.", "School subscriptions and NGO grants; freemium for individual learners."),
        (arjun, "Leaf-Photo Crop Disease Triage for Smallholders", "Farmers photograph a diseased leaf and receive likely causes and low-cost treatment options in their own language.",
         "Smallholder farmers often notice crop disease late and lack affordable access to agronomists, which leads to avoidable yield loss and over-use of pesticides.",
         "A mobile app using an on-device image classifier trained on labelled leaf images to suggest probable diseases, together with locally available treatment guidance and a way to request a human agronomist review.",
         "AgriTech", "Smallholder farmers and agricultural extension officers", ["Computer Vision", "Mobile App"], "research", "restricted", 80000,
         "Reduces yield loss and unnecessary pesticide use.", "Subscription for cooperatives, B2B contracts with input suppliers."),
        (lena, "Neighbourhood Tool Library with Smart Lockers", "A shared tool-lending service where residents borrow drills, ladders and gardening tools from QR-locked neighbourhood lockers.",
         "Most households use power tools only a few times a year, yet buy and store them, which wastes money, space and resources.",
         "Community lockers placed in apartment blocks hold shared tools. Residents reserve through an app, unlock with a QR code and are charged a small fee or deposit; a deposit system and condition photos handle damage.",
         "Social Impact", "Apartment residents and community associations", ["Mobile App", "IoT", "Hardware"], "concept", "public", 40000,
         "Cuts consumption and builds community.", "Membership fees, per-use fees and sponsorship from hardware retailers."),
        (maya, "Study Group Matching by Learning Style", "An app that matches university students into study groups based on course, schedule and complementary strengths.",
         "Students struggle to find reliable study partners, and groups formed by chance are often mismatched in schedule and ability.",
         "Students enter courses, availability and self-assessed strengths; the app proposes groups, schedules sessions and offers shared flashcards and notes.",
         "EdTech", "University students", ["Web App", "AI / ML"], "concept", "public", 15000,
         "Improves collaborative learning and retention.", "Freemium with premium analytics for universities."),
        (arjun, "Soil Moisture Sensor Mesh for Small Orchards", "Low-cost wireless soil sensors that tell orchard owners when and where to irrigate.",
         "Over- and under-irrigation waste water and reduce fruit quality, but commercial moisture systems are priced for large farms.",
         "Solar-powered sensor nodes form a low-power radio mesh and report to a farm hub that recommends irrigation schedules using simple thresholds and weather inputs.",
         "AgriTech", "Small orchard owners", ["IoT", "Hardware", "Data Analytics"], "prototype", "private", 120000,
         "Saves water and raises yields.", "Hardware sales plus a subscription for analytics."),
        (lena, "Plain-Language Contract Explainer for Freelancers", "A tool that highlights unusual clauses in freelance contracts and explains them in plain language.",
         "Freelancers sign contracts without legal review and miss clauses about payment terms, IP ownership and liability.",
         "A web app where users paste a contract; language models flag clauses against a checklist of common risk areas and produce plain-language explanations with questions to ask the client. It does not provide legal advice.",
         "AI / Machine Learning", "Independent freelancers and small agencies", ["NLP", "Web App"], "mvp", "public", 50000,
         "Reduces costly contract disputes for freelancers.", "Subscription and pay-per-review pricing."),
    ]
    made = []
    for owner, title, short, prob, sol, ind, aud, tech, stage, vis, fund, impact, biz in ideas:
        i = Idea(creator_id=owner.id, title=title, short_description=short, problem=prob, solution=sol, industry=ind,
                 target_audience=aud, technologies=tech, stage=stage, visibility=vis, funding_needed=fund,
                 expected_impact=impact, business_potential=biz)
        db.add(i)
        made.append(i)
    db.flush()
    db.add(CollaborationRequest(idea_id=made[0].id, entrepreneur_id=ravi.id, creator_id=maya.id, kind="fund",
                                message="We back education tools and would like to discuss a pilot with rural schools."))
    db.add(Message(sender_id=ravi.id, recipient_id=maya.id, idea_id=made[0].id,
                   body="Hi Maya, your offline flashcards concept fits our portfolio. Do you have a pilot plan?"))
    db.commit()
    for i in made:
        ev = create_evaluation(db, i)
        run_evaluation(ev.id, force_demo=True)
    log.info("Demo data seeded (password for all demo users: %s)", DEMO_PASSWORD)


def bootstrap(db: Session) -> None:
    s = get_settings()
    ensure_categories(db)
    vectors.ensure_reference_projects(db)
    ensure_admin(db)
    if s.seed_demo_data:
        seed_demo(db)
