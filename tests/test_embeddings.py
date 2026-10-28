from src.embeddings import MAX_COMMENT_CHARS, build_clinical_text, vector_literal


def test_builds_text_from_present_fields_only():
    row = {"admission_type": "URGENT", "drug": "Furosemide", "test_name": None, "comments": ""}
    assert build_clinical_text(row) == "Admission: URGENT | Prescribed: Furosemide"


def test_comments_are_truncated():
    text = build_clinical_text({"comments": "x" * 1000})
    assert text == "Notes: " + "x" * MAX_COMMENT_CHARS


def test_empty_row_still_yields_text():
    assert build_clinical_text({}) == "Encounter record"


def test_vector_literal_format():
    assert vector_literal([0.5, 1, -2.25]) == "[0.5,1,-2.25]"
