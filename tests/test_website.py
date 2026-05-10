"""Tests for website collector utilities."""

from prism_analyst.collect.website import normalize_domain, _extract_text, _extract_meta


def test_normalize_domain_from_url():
    assert normalize_domain("https://www.stripe.com/payments") == "stripe.com"


def test_normalize_domain_plain():
    assert normalize_domain("stripe.com") == "stripe.com"


def test_normalize_domain_with_subdomain():
    assert normalize_domain("https://docs.stripe.com") == "stripe.com"


def test_normalize_domain_name_only():
    assert normalize_domain("Stripe") == "stripe"


def test_extract_text():
    html = "<html><body><p>Hello World</p><script>var x=1;</script></body></html>"
    text = _extract_text(html)
    assert "Hello World" in text
    assert "var x" not in text


def test_extract_meta():
    html = '<html><head><title>Test Page</title><meta name="description" content="A test"></head><body></body></html>'
    meta = _extract_meta(html)
    assert meta["title"] == "Test Page"
    assert meta["description"] == "A test"
