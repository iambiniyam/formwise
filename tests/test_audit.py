import json

import pytest

from formwise.audit import load_audit, totals


def test_audit_reader_summarizes(tmp_path):
    path = tmp_path / "audit.json"
    path.write_text(json.dumps({
        "tool": "formwise",
        "files": [
            {"input": "a.pdf", "pages": 1, "fields": 2, "filled": 2, "blank": []},
            {"input": "b.pdf", "pages": 2, "fields": 3, "filled": 1, "blank": ["email"], "error": "bad form"},
        ],
    }))
    payload = load_audit(path)
    summary = totals(payload)
    assert summary == {"files": 2, "errors": 1, "fields": 5, "filled": 3}


def test_audit_rejects_other_json(tmp_path):
    path = tmp_path / "other.json"
    path.write_text(json.dumps({"tool": "something-else"}))
    with pytest.raises((TypeError, ValueError)):
        load_audit(path)
