"""08 §7: normalisation, MinHash, LSH, distinctive sentence; P10 findings. T3.5."""
from pathlib import Path

from test_probes_core import FakeSerp, codes, ctx

from special26.claims.extract import extract_claims
from special26.probes.p10_template import P10Template
from special26.storage.retention import seed_templates
from special26.template.minhash import band_keys, from_blob, jaccard_est, signature, to_blob
from special26.template.normalize import tokens
from special26.template.phrase import distinctive_sentence

GOLDEN = Path(__file__).parents[1] / "golden/inputs"
BASE = ("Dear candidate, we are pleased to inform you that you have been shortlisted for the post of trainee analyst "
        "in our organisation after careful review of your resume and academic record. To confirm your seat you must "
        "complete the document verification process and pay the refundable onboarding charges before the deadline, "
        "after which your appointment letter and joining kit will be dispatched to your registered address by courier.")


def test_placeholders():
    g1 = (GOLDEN / "g1.txt").read_text()
    toks = tokens(g1, extract_claims(g1))
    for ph in ("<recipient>", "<org>", "<amt>", "<upi>", "<phone>", "<email>", "<per>", "<num>"):
        assert ph in toks, ph
    assert "mahindra" not in toks and "ritika" not in toks and "2" not in toks


def test_signature_self_match_and_paraphrase():
    a = signature(tokens(BASE))
    assert jaccard_est(a, signature(tokens(BASE))) == 1.0
    para = (BASE.replace("pleased", "happy").replace("careful review", "detailed review")
            .replace("dispatched", "sent").replace("before the deadline", "within two days"))
    j = jaccard_est(a, signature(tokens(para)))
    assert 0.4 <= j <= 0.8, j
    unrelated = signature(tokens("The quarterly results show revenue grew in every segment, " * 6))
    assert jaccard_est(a, unrelated) < 0.1


def test_short_text_has_no_signature_and_blob_roundtrip():
    assert signature(tokens("too short to fingerprint")) is None
    s = signature(tokens(BASE))
    assert from_blob(to_blob(s)) == s and len(to_blob(s)) == 1024 and len(band_keys(s)) == 32


def test_lsh_candidates_and_seed_loader(repo, tmp_path, monkeypatch):
    from special26 import seeds
    d = tmp_path / "scam_templates"
    d.mkdir()
    (d / "news1.txt").write_text("# source: https://news.example/a\n" + BASE)
    monkeypatch.setattr(seeds, "DIR", tmp_path)
    assert seed_templates(repo) == 1
    hits = repo.template_candidates(signature(tokens(BASE)), label="scam")
    assert hits[0]["check_id"] == "seed:news1.txt" and hits[0]["jaccard"] == 1.0
    assert hits[0]["source_url"] == "https://news.example/a"


def test_distinctive_sentence_skips_recipient_and_trims():
    s = distinctive_sentence((GOLDEN / "g1.txt").read_text())
    assert s and "<RECIPIENT>" not in s and len(s.split()) <= 20


async def test_p10_template_high_and_phrase_reported(repo, tmp_path, monkeypatch):
    from special26 import seeds
    d = tmp_path / "scam_templates"
    d.mkdir()
    (d / "a.txt").write_text("# source: https://news.example/a\n" + BASE)
    monkeypatch.setattr(seeds, "DIR", tmp_path)
    seed_templates(repo)
    c = ctx(BASE + " Kindly keep this selection strictly confidential and do not discuss it with your friends.")
    c.repo = repo
    sentence = distinctive_sentence(c.redacted_text, c.claims)
    serp = FakeSerp({f'"{sentence}"': {"organic_results": [
        {"position": 1, "title": "Beware of this fake offer letter", "link": "https://alerts.example.in/x"}]}})
    c.serp = serp
    res = await P10Template().run(c)
    assert codes(res) == ["P10_TEMPLATE_MATCH_HIGH", "P10_PHRASE_REPORTED"]
    assert res.findings[0].receipt.link == "https://news.example/a" and res.findings[0].receipt.extra["similarity"] >= 0.6
    assert "%" not in res.findings[0].message


def test_p10_skipped_on_tiny_text():
    assert P10Template().applicable(ctx("Hi")) == "skipped_no_input"
