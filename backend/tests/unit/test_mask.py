"""03 §4.3, D-20, FR-42."""
from special26.scoring.mask import mask_email, mask_phone, mask_text, mask_upi


def test_masks():
    assert mask_phone("+919876543210") == "+91 ******3210"            # FR-42 acceptance
    assert mask_upi("techm.hr@ybl") == "te****@ybl"
    assert mask_email("hr.onboarding@techmahindra-careers.in") == "h***@techmahindra-careers.in"


def test_mask_text_snippet():
    s = "Pay techm.hr@ybl or mail hr.onboarding@techmahindra-careers.in or call +91 98765 43210 at techmahindra.com"
    assert mask_text(s) == ("Pay te****@ybl or mail h***@techmahindra-careers.in or call +91 ******3210 at "
                            "techmahindra.com")
    assert mask_text(None) is None
