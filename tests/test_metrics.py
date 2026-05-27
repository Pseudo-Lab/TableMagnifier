from table_agi_bench.eval.metrics import efficiency_score, is_correct_answer


def test_string_match():
    assert is_correct_answer(" RX-1 ", "rx-1", "string")


def test_integer_match():
    assert is_correct_answer("1,024", 1024, "integer")


def test_wrong_answer_zero_efficiency():
    assert efficiency_score(action_count=10, human_baseline_actions=10, correct=False) == 0.0


def test_efficiency_cap():
    assert efficiency_score(action_count=5, human_baseline_actions=10, correct=True) == 1.0


def test_efficiency_square():
    assert abs(efficiency_score(action_count=100, human_baseline_actions=10, correct=True) - 0.01) < 1e-12
