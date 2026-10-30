from privacy import redact_personal_information


def test_redacts_email_phone_pan_and_aadhaar_like_numbers():
    text = (
        "Email alice@example.com, phone +91 9876543210, "
        "PAN ABCDE1234F and ID 1234 5678 9012."
    )
    redacted = redact_personal_information(text)
    assert "alice@example.com" not in redacted
    assert "9876543210" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "1234 5678 9012" not in redacted


def test_leaves_non_matching_text_unchanged():
    assert redact_personal_information("Section 103 applies.") == (
        "Section 103 applies."
    )
