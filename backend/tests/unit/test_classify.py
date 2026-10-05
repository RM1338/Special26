"""05 §5 table (all 12 rows) plus extras. FR-20 inputs for P02."""
import pytest

from special26.domains.classify import classify, platform_kind, reg

ROWS = [
    ("careers.techmahindra.com", "techmahindra.com", "official_subdomain"),
    ("techmahindra-careers.in", "techmahindra.com", "combosquat"),
    ("careers-github.com", "github.com", "combosquat"),
    ("techmahindra.co.in", "techmahindra.com", "tld_swap"),
    ("tecmahindra.com", "techmahindra.com", "typosquat"),
    ("infosys-hr.xyz", "infosys.com", "combosquat"),
    ("lnfosys.com", "infosys.com", "homoglyph"),
    ("tcs.hr-onboarding.in", "tcs.com", "combosquat"),
    ("gmail.com", "tcs.com", "freemail"),
    ("forms.gle", "tcs.com", "platform"),
    ("hiringdesk-global.com", "tcs.com", "unrelated"),
    ("tcsion.com", "tcs.com", "unrelated"),
    # extras
    ("techmahindra.com", "techmahindra.com", "official"),
    ("www.techmahindra.com", "techmahindra.com", "official"),
    ("techrnahindra.com", "techmahindra.com", "homoglyph"),
    ("tеchmahindra.com", "techmahindra.com", "homoglyph"),           # Cyrillic е -> xn--
    ("techmahindara.com", "techmahindra.com", "typosquat"),
    ("techmahindra.org", "techmahindra.com", "tld_swap"),
    ("infosys-careers.co", "infosys.com", "combosquat"),              # G6a
    ("hcltech-hiring.in", "hcltech.com", "combosquat"),               # G6b
    ("techmahindra.hr-portal.in", "techmahindra.com", "combosquat"),
    ("docs.google.com", "tcs.com", "unrelated"),                     # bare docs host is not a platform
    ("hdfc.bank.in", "hdfcbank.com", "unrelated"),                    # D-30: bank.in is a suffix
]


@pytest.mark.parametrize("d,official,expected", ROWS)
def test_classify_table(d, official, expected):
    assert classify(d, {official})[0] == expected


def test_official_set_with_subdomain_entry():
    assert classify("pminternship.mca.gov.in", {"pminternship.mca.gov.in", "mca.gov.in"})[0] == "official_subdomain"


def test_empty_official_set():
    assert classify("nimbleleaf.in", set())[0] == "unrelated"
    assert classify("gmail.com", set())[0] == "freemail"


def test_bank_in_registrable():  # D-30
    assert reg("www.hdfc.bank.in") == "hdfc.bank.in" and reg("sbi.bank.in") != reg("hdfc.bank.in")


@pytest.mark.parametrize("u,kind", [("https://forms.gle/abc", "form"), ("https://docs.google.com/forms/d/x", "form"),
                                    ("https://docs.google.com/document/d/x", "document"), ("bit.ly/x", "shortener"),
                                    ("https://wa.me/919876543210", "messaging"), ("upi://pay?pa=x@ybl", "payment"),
                                    ("https://rzp.io/l/abc", "payment"), ("https://www.techmahindra.com", None)])
def test_platform_kind(u, kind):
    assert platform_kind(u) == kind
