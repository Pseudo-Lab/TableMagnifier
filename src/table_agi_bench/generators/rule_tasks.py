from __future__ import annotations

import random
import string
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from table_agi_bench.core.types import Cell, TaskSpec
from table_agi_bench.generators.v3_contract import (
    action_contract,
    evidence_cell,
    finalize_v3_task,
    validate_v3_task,
)


def _token(rng: random.Random, prefix: str, n: int = 3) -> str:
    return prefix + "-" + "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def _header(text: str) -> Cell:
    return Cell(text=text, bg="#e5e7eb", fg="#111111", bold=True)


@dataclass(frozen=True)
class _SymbolRule:
    op: str
    amount: int

    def apply(self, value: int) -> int:
        if self.op == "add":
            return value + self.amount
        if self.op == "subtract":
            return value - self.amount
        if self.op == "multiply":
            return value * self.amount
        raise ValueError(f"unsupported symbol op: {self.op}")

    @property
    def display(self) -> str:
        if self.op == "add":
            return f"+{self.amount}"
        if self.op == "subtract":
            return f"-{self.amount}"
        if self.op == "multiply":
            return f"x{self.amount}"
        return self.op


_FORBIDDEN_VISIBLE_TERMS = {
    "answer",
    "gold",
    "target answer",
    "distractor",
    "rationale",
    "debug",
    "generation",
    "정답",
    "오답",
    "후보",
    "검산",
    "숨김",
    "단서 적용 후보",
}


def _parse_symbol_token(token: str) -> tuple[int, str]:
    digits = "".join(ch for ch in token if ch.isdigit() or ch == "-")
    symbol = token.replace(digits, "")
    return int(digits), symbol


def _row_marker_rule(marker: str, marker_rules: dict[str, _SymbolRule]) -> _SymbolRule:
    return marker_rules[marker]


def _apply_cells_then_marker(tokens: list[str], rules: dict[str, _SymbolRule], marker: str, marker_rules: dict[str, _SymbolRule]) -> int:
    total = 0
    for token in tokens:
        value, symbol = _parse_symbol_token(token)
        total += rules[symbol].apply(value)
    return _row_marker_rule(marker, marker_rules).apply(total)


def _apply_marker_then_cells(tokens: list[str], rules: dict[str, _SymbolRule], marker: str, marker_rules: dict[str, _SymbolRule]) -> int:
    raw_total = sum(_parse_symbol_token(token)[0] for token in tokens)
    marked_total = _row_marker_rule(marker, marker_rules).apply(raw_total)
    symbol_delta = sum(rules[_parse_symbol_token(token)[1]].apply(0) for token in tokens)
    return marked_total + symbol_delta


def _swap_first_two_rules(rules: dict[str, _SymbolRule]) -> dict[str, _SymbolRule]:
    swapped = dict(rules)
    symbols = list(swapped)
    swapped[symbols[0]], swapped[symbols[1]] = swapped[symbols[1]], swapped[symbols[0]]
    return swapped


def _visible_text(table: list[list[Cell]]) -> str:
    return " ".join(cell.text for row in table for cell in row)


def validate_symbol_adjusted_score_task(task: TaskSpec) -> dict[str, Any]:
    """Validate the v3 symbolic-cell anti-shortcut contract for one task."""
    return validate_v3_task(task)


def generate_symbol_adjusted_score_task(seed: int = 0, level: int = 2) -> TaskSpec:
    """Generate the v3 `symbol_adjusted_score` Visual TableQA template.

    The task requires reading workbook-local glyph rules before calculating the
    adjusted score. Hidden solver details and trap derivations stay private.
    """

    if level not in {1, 2, 3}:
        raise ValueError("level must be 1, 2, or 3")

    rng = random.Random(seed + level * 10_000)
    symbols = rng.sample(["★", "▲", "●", "◆", "◇", "■", "△", "◎", "✦"], 4)
    marker_symbols = rng.sample([symbol for symbol in symbols if symbol not in symbols[:2]], 2)
    cell_symbols = symbols[:3 if level >= 2 else 2]

    op_bank = [
        _SymbolRule("add", rng.randint(3, 9)),
        _SymbolRule("subtract", rng.randint(2, 7)),
        _SymbolRule("multiply", rng.randint(2, 3)),
    ]
    rng.shuffle(op_bank)
    symbol_rules = {symbol: op_bank[index] for index, symbol in enumerate(cell_symbols)}
    marker_rules = {
        marker_symbols[0]: _SymbolRule("add", rng.randint(4, 10)),
        marker_symbols[1]: _SymbolRule("subtract", rng.randint(3, 8)),
    }
    if level == 1:
        marker_rules = {symbol: _SymbolRule("add", 0) for symbol in marker_symbols}

    target_id = _token(rng, "V", 3)
    segment = _token(rng, "S", 2)
    records: list[dict[str, Any]] = []
    for index in range(8 + level * 2):
        rec_symbols = [rng.choice(cell_symbols) for _ in range(2 + (level >= 2))]
        values = [rng.randint(11, 46) for _ in rec_symbols]
        rec = {
            "id": _token(rng, "V", 3),
            "segment": rng.choice([segment, _token(rng, "S", 2), _token(rng, "S", 2)]),
            "tokens": [f"{value}{symbol}" for value, symbol in zip(values, rec_symbols, strict=True)],
            "marker": rng.choice(marker_symbols),
        }
        records.append(rec)

    target_index = rng.randrange(len(records))
    records[target_index]["id"] = target_id
    records[target_index]["segment"] = segment
    records[target_index]["marker"] = marker_symbols[0] if level >= 2 else marker_symbols[1]

    if level == 3:
        exception_symbol = cell_symbols[-1]
        forced_value = rng.randint(17, 39)
        records[target_index]["tokens"][-1] = f"{forced_value}{exception_symbol}"
        symbol_rules[exception_symbol] = _SymbolRule("subtract", rng.randint(6, 11))

    target_tokens = list(records[target_index]["tokens"])
    target_marker = str(records[target_index]["marker"])
    gold = _apply_cells_then_marker(target_tokens, symbol_rules, target_marker, marker_rules)
    distractor_builders: list[tuple[str, Callable[[], int]]] = [
        ("symbol_ignore", lambda: sum(_parse_symbol_token(token)[0] for token in target_tokens)),
        (
            "wrong_symbol_rule",
            lambda: _apply_cells_then_marker(target_tokens, _swap_first_two_rules(symbol_rules), target_marker, marker_rules),
        ),
    ]
    if level >= 2:
        distractor_builders.append(
            (
                "operation_order",
                lambda: _apply_marker_then_cells(target_tokens, symbol_rules, target_marker, marker_rules),
            )
        )
    if level >= 3:
        distractor_builders.append(
            (
                "exception_skip",
                lambda: _apply_cells_then_marker(
                    target_tokens,
                    {**symbol_rules, cell_symbols[-1]: _SymbolRule("add", 0)},
                    target_marker,
                    marker_rules,
                ),
            )
        )

    distractors: list[dict[str, Any]] = []
    used = {gold}
    for trap_id, build in distractor_builders:
        value = build()
        while value in used:
            value += len(used) + level
        used.add(value)
        distractors.append({"trap_id": trap_id, "value": value, "display_value": str(value)})

    rows: list[list[Cell]] = []
    rows.append([_header("SYMBOL SCORE SHEET"), Cell(""), Cell(""), Cell(""), Cell(""), Cell("")])
    rows.append([_header("ITEM"), _header("SEG"), _header("M1"), _header("M2"), _header("M3"), _header("ROW MARK")])
    for rec in records:
        highlight = "#fef9c3" if rec["id"] == target_id else "#ffffff"
        token_cells = [Cell(text, bg=highlight) for text in rec["tokens"]]
        while len(token_cells) < 3:
            token_cells.append(Cell("", bg=highlight))
        rows.append(
            [
                Cell(str(rec["id"]), bg=highlight),
                Cell(str(rec["segment"]), bg=highlight),
                *token_cells,
                Cell(str(rec["marker"]), bg=highlight),
            ]
        )

    rows.append([Cell("") for _ in range(6)])
    rows.append([_header("LOCAL RULES"), Cell(""), Cell(""), Cell(""), Cell(""), Cell("")])
    rows.append([_header("GLYPH"), _header("CELL ADJ"), _header("ROW ADJ"), _header("ORDER"), Cell(""), Cell("")])
    for symbol, rule in symbol_rules.items():
        rows.append([Cell(symbol), Cell(rule.display), Cell(""), Cell("cell first"), Cell(""), Cell("")])
    for symbol, rule in marker_rules.items():
        rows.append([Cell(symbol), Cell(""), Cell(rule.display), Cell("after sum"), Cell(""), Cell("")])

    evidence = [target_id, segment, *cell_symbols, *marker_symbols]
    nav_tier = "A" if level == 1 else "B"
    estimated_action_floor = 8 if level == 1 else 16 if level == 2 else 22
    data_row = target_index + 2
    rules_header_row = 4 + len(records)
    evidence_cells = [
        evidence_cell(data_row, 0, "target"),
        evidence_cell(data_row, 2, "target"),
        evidence_cell(data_row, 5, "target"),
        evidence_cell(rules_header_row, 0, "legend"),
        evidence_cell(rules_header_row + 1, 1, "rule"),
    ]
    contract = action_contract(
        nav_tier,
        estimated_action_floor,
        evidence_cells,
        estimated_human_mean_actions=32.0 if level == 1 else 48.0 if level == 2 else 58.0,
        estimated_human_second_best_actions=22.0 if level == 1 else 34.0 if level == 2 else 44.0,
    )
    private_metadata: dict[str, Any] = {
        "template_id": "symbol_adjusted_score",
        "family_id": "k_vis_table_arc",
        "skill_ids": ["symbolic_cells"],
        "visual_extensions_used": ["viewportMeta"],
        "action_contract": contract,
        "gold_evidence_path": evidence_cells,
        "diagnostics": {
            "reasoning_level": level,
            "nav_tier": nav_tier,
            "primary_failure_modes": ["symbol_grounding", "legend_lookup", "operation_order"],
        },
        "skill_plan": {
            "selected_skill_ids": ["symbolic_cells"],
            "primary_template_id": "symbol_adjusted_score",
            "level": level,
            "nav_tier": nav_tier,
            "answer_form": "number",
            "assumptions": ["Current renderer supports glyph text in cells; this template only requires viewportMeta."],
        },
        "hidden_program_shape": "parse numeric+symbol tokens -> lookup glyph operations -> apply cell adjustments -> aggregate -> apply row marker",
        "target_item": target_id,
        "target_segment": segment,
        "target_tokens": target_tokens,
        "target_marker": target_marker,
        "symbol_rules": {symbol: rule.display for symbol, rule in symbol_rules.items()},
        "marker_rules": {symbol: rule.display for symbol, rule in marker_rules.items()},
        "required_visible_evidence": evidence,
        "shortcut_traps": [item["trap_id"] for item in distractors],
        "distractor_derivations": distractors,
        "minimum_trap_count": 2 if level == 1 else 3 if level == 2 else 4,
        "symbol_evidence_path": [
            {"region": "data", "item": target_id, "tokens": target_tokens, "marker": target_marker},
            {"region": "local_rules", "symbols": cell_symbols, "markers": marker_symbols},
        ],
    }

    task = TaskSpec(
        task_id=f"symbol_adjusted_score_l{level}_{seed:06d}",
        split="dev",
        seed=seed,
        question=(
            f"LOCAL RULES를 사용해 ITEM {target_id}, SEG {segment} 행의 M 셀 조정값을 모두 더한 뒤 "
            "ROW MARK 조정을 적용한 최종 수치를 제출하세요."
        ),
        answer=gold,
        answer_type="integer",
        table=rows,
        tags=[
            "abc_v3",
            "symbolic_cells",
            "symbol_adjusted_score",
            "legend_lookup",
            "operation_order",
            "excel_style",
        ],
        max_actions=140 if level == 1 else 180,
        human_mean_actions=32.0 if level == 1 else 48.0 if level == 2 else 58.0,
        human_second_best_actions=22.0 if level == 1 else 34.0 if level == 2 else 44.0,
        human_median_actions=30.0 if level == 1 else 46.0 if level == 2 else 55.0,
        private_metadata=private_metadata,
    )
    return finalize_v3_task(task)


def generate_rule_key_rank_task(seed: int = 0, n_rows: int = 36) -> TaskSpec:
    """Generate a task-local rule + ranking table QA task.

    The task is intentionally synthetic. The table contains a DATA TABLE and a KEY TABLE.
    The question can only be answered by reading both regions and applying the task-local rule.
    """
    rng = random.Random(seed)
    groups = [_token(rng, "G") for _ in range(5)]
    tokens = [_token(rng, "T") for _ in range(4)]
    focus_group = rng.choice(groups)
    active_token = rng.choice(tokens)

    rows: list[list[Cell]] = []
    rows.append([_header("DATA TABLE"), Cell(""), Cell(""), Cell(""), Cell(""), Cell("")])
    rows.append([_header("ID"), _header("GROUP"), _header("A"), _header("B"), _header("TOKEN"), _header("NOTE")])

    records: list[dict[str, int | str]] = []
    for _ in range(n_rows):
        rec = {
            "ID": _token(rng, "R", 4),
            "GROUP": rng.choice(groups),
            "A": rng.randint(10, 99),
            "B": rng.randint(10, 99),
            "TOKEN": rng.choice(tokens),
            "NOTE": _token(rng, "N", 2),
        }
        records.append(rec)

    # Ensure at least one matching row.
    forced = rng.randrange(n_rows)
    records[forced]["GROUP"] = focus_group
    records[forced]["TOKEN"] = active_token

    # Visual color rule: active token rows are lightly highlighted, but the text rule remains in KEY TABLE.
    for rec in records:
        bg = "#fff7cc" if rec["TOKEN"] == active_token else "#ffffff"
        rows.append(
            [
                Cell(str(rec["ID"]), bg=bg),
                Cell(str(rec["GROUP"]), bg=bg),
                Cell(str(rec["A"]), bg=bg),
                Cell(str(rec["B"]), bg=bg),
                Cell(str(rec["TOKEN"]), bg=bg),
                Cell(str(rec["NOTE"]), bg=bg),
            ]
        )

    # Blank spacer rows.
    rows.append([Cell("") for _ in range(6)])
    rows.append([_header("KEY TABLE"), Cell(""), Cell(""), Cell(""), Cell(""), Cell("")])
    rows.append([_header("MARKER"), _header("KEY"), _header("VALUE"), Cell(""), Cell(""), Cell("")])
    rows.append([Cell("FOCUS"), Cell("GROUP"), Cell(focus_group), Cell(""), Cell(""), Cell("")])
    rows.append([Cell("ACTIVE"), Cell("TOKEN"), Cell(active_token), Cell(""), Cell(""), Cell("")])
    rows.append([Cell("RULE"), Cell("SCORE"), Cell("B minus A"), Cell(""), Cell(""), Cell("")])

    candidates = [rec for rec in records if rec["GROUP"] == focus_group and rec["TOKEN"] == active_token]
    best = max(candidates, key=lambda rec: int(rec["B"]) - int(rec["A"]))
    answer = str(best["ID"])

    question = (
        "Use the KEY TABLE to find the FOCUS GROUP and ACTIVE TOKEN. "
        "In the DATA TABLE, among rows matching both of those values, compute SCORE = B - A. "
        "What is the ID of the row with the largest SCORE?"
    )

    return TaskSpec(
        task_id=f"rule_key_rank_{seed:06d}",
        split="dev",
        seed=seed,
        question=question,
        answer=answer,
        answer_type="string",
        table=rows,
        tags=["semantic_lookup", "conditional_ranking", "task_local_rule", "excel_style"],
        max_actions=160,
        human_mean_actions=42.0,
        human_second_best_actions=28.0,
        human_median_actions=39.0,
        private_metadata={
            "focus_group": focus_group,
            "active_token": active_token,
            "best_score": int(best["B"]) - int(best["A"]),
            "num_candidates": len(candidates),
        },
    )
