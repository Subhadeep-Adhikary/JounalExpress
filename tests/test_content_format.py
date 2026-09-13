from app.routes.tasks import _rows_to_text


def test_rows_to_text_prefers_plain_content():
    payload = {
        "content": "This is the exact text\nI wrote in the editor.",
        "content_rows": [{"line": "not used"}],
    }

    assert _rows_to_text(payload) == "This is the exact text\nI wrote in the editor."


def test_rows_to_text_parses_stringified_line_json():
    payload = '[{"line": "here is something to write."}]'

    assert _rows_to_text(payload) == "here is something to write."
