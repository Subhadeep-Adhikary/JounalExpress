from app.routes.tasks import _rows_to_text
from app.security import encrypt_json


def test_rows_to_text_prefers_plain_content():
    payload = {
        "content": "This is the exact text\nI wrote in the editor.",
        "content_rows": [{"line": "not used"}],
    }

    assert _rows_to_text(payload) == "This is the exact text\nI wrote in the editor."


def test_rows_to_text_parses_stringified_line_json():
    payload = '[{"line": "here is something to write."}]'

    assert _rows_to_text(payload) == "here is something to write."


def test_rows_to_text_decrypts_encrypted_line_json():
    payload = encrypt_json([{"line": "here is something to write."}])

    assert _rows_to_text(payload) == "here is something to write."
