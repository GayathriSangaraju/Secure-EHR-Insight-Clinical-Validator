from src.output_checks import check_grounding, grounding_warning

CONTEXT = "Drug: Furosemide (40 mg), Route: IV. Potassium 4.50 mmol. Admitted 2180."


def test_figures_present_in_context_are_grounded():
    assert check_grounding("The last dose was 40mg IV.", CONTEXT).grounded


def test_invented_dose_is_flagged():
    result = check_grounding("The last dose was 80 mg.", CONTEXT)
    assert not result.grounded
    assert result.ungrounded == ["80mg"]


def test_unit_mismatch_is_flagged():
    assert not check_grounding("They received 40 units.", CONTEXT).grounded


def test_decimal_formatting_is_normalised():
    assert check_grounding("Potassium was 4.5 mmol.", CONTEXT).grounded


def test_list_markers_and_small_counts_are_ignored():
    assert check_grounding("1. Furosemide\n2. Admitted\n3 records found.", CONTEXT).grounded


def test_answer_without_figures_is_grounded():
    assert check_grounding("I cannot find that in the record.", CONTEXT).grounded


def test_warning_text():
    assert grounding_warning(check_grounding("Dose 80 mg", CONTEXT)).startswith("Some figures")
    assert grounding_warning(check_grounding("Dose 40 mg", CONTEXT)) is None
