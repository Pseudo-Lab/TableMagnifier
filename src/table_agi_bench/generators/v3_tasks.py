from __future__ import annotations

import random
import string
from typing import Any

from table_agi_bench.core.types import Cell, TaskSpec
from table_agi_bench.generators.v3_contract import (
    action_contract,
    evidence_cell,
    finalize_v3_task,
    unique_distractors,
    v3_metadata,
    validate_v3_task,
)

V3_TASK_FAMILIES = [
    "merged_group_header_delta",
    "symbol_adjusted_score",
    "cell_icon_legend_count",
    "massive_sparse_anchor_lookup",
    "multipage_index_rule_lookup",
    "compound_merged_symbol_multipage",
]

_SYMBOLS = ["★", "▲", "●", "◆", "◇", "■", "△", "◎", "✦"]


def _rng(seed: int, level: int, offset: int) -> random.Random:
    return random.Random(seed + level * 10_000 + offset)


def _token(rng: random.Random, prefix: str, n: int = 3) -> str:
    return prefix + "-" + "".join(rng.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def _header(text: str) -> Cell:
    return Cell(text=text, bg="#e5e7eb", fg="#111111", bold=True)


def _page(text: str) -> list[Cell]:
    return [_header(text), Cell(""), Cell(""), Cell(""), Cell(""), Cell("")]


def _blank(width: int) -> list[Cell]:
    return [Cell("") for _ in range(width)]


def _apply_rule(display_rule: str, value: int) -> int:
    if display_rule.startswith("+"):
        return value + int(display_rule[1:])
    if display_rule.startswith("-"):
        return value - int(display_rule[1:])
    if display_rule.startswith("x"):
        return value * int(display_rule[1:])
    return value


def _parse_token(token: str) -> tuple[int, str]:
    digits = "".join(ch for ch in token if ch.isdigit() or ch == "-")
    return int(digits), token.replace(digits, "")


def _common_task(
    *,
    task_id: str,
    seed: int,
    question: str,
    answer: Any,
    answer_type: str,
    table: list[list[Cell]],
    tags: list[str],
    max_actions: int,
    human_mean_actions: float,
    human_second_best_actions: float,
    private_metadata: dict[str, Any],
) -> TaskSpec:
    return finalize_v3_task(
        TaskSpec(
            task_id=task_id,
            split="dev",
            seed=seed,
            question=question,
            answer=answer,
            answer_type=answer_type,  # type: ignore[arg-type]
            table=table,
            tags=["abc_v3", *tags, "excel_style"],
            max_actions=max_actions,
            human_mean_actions=human_mean_actions,
            human_second_best_actions=human_second_best_actions,
            human_median_actions=human_mean_actions - 2,
            private_metadata=private_metadata,
        )
    )


def generate_merged_group_header_delta_task(seed: int = 0, level: int = 2) -> TaskSpec:
    if level not in {1, 2, 3}:
        raise ValueError("level must be 1, 2, or 3")
    rng = _rng(seed, level, 1_000)
    groups = [f"Cycle {name}" for name in rng.sample(["A", "B", "C", "D"], 3 if level >= 2 else 2)]
    subheaders = ["Base", "Adjust", "Mark"]
    target_label = _token(rng, "K", 2)
    target_status = _token(rng, "ST", 1)
    row_count = 6 + level * 3
    target_index = rng.randrange(3, row_count)

    rows: list[list[Cell]] = []
    width = 1 + len(groups) * len(subheaders)
    rows.append([_header("MERGED CYCLE SHEET"), *_blank(width - 1)])
    rows.append([_header("ITEM"), *[Cell(group, bg="#dbeafe", bold=True) for group in groups for _ in subheaders]])
    rows.append([_header("ITEM"), *[_header(subheader) for _ in groups for subheader in subheaders]])

    records: list[dict[str, Any]] = []
    for idx in range(row_count):
        label = target_label if idx == target_index else _token(rng, "K", 2)
        rec = {"label": label, "values": {}}
        for group in groups:
            base = rng.randint(30, 90)
            adjust = rng.randint(5, 28)
            rec["values"][group] = {
                "Base": base,
                "Adjust": adjust,
                "Mark": rng.choice(_SYMBOLS[:6]),
            }
        records.append(rec)

    left_group, right_group = groups[0], groups[1]
    # Make the target delta non-zero and stable.
    records[target_index]["values"][left_group]["Adjust"] = rng.randint(8, 20)
    records[target_index]["values"][right_group]["Adjust"] = records[target_index]["values"][left_group]["Adjust"] + rng.randint(7, 19)
    raw_delta = records[target_index]["values"][right_group]["Adjust"] - records[target_index]["values"][left_group]["Adjust"]
    multiplier = 2 if level == 3 else 1
    gold = raw_delta * multiplier

    for rec in records:
        bg = "#fef9c3" if rec["label"] == target_label else "#ffffff"
        row = [Cell(str(rec["label"]), bg=bg)]
        for group in groups:
            for subheader in subheaders:
                row.append(Cell(str(rec["values"][group][subheader]), bg=bg))
        rows.append(row)

    note_row = len(rows) + 2
    rows.append(_blank(width))
    rows.append([_header("WORKBOOK NOTE"), Cell("STATUS"), Cell(target_status), Cell("DELTA MULT"), Cell(f"x{multiplier}"), *_blank(width - 5)])

    flat_adjust = records[target_index]["values"][groups[0]]["Adjust"]
    wrong_header = records[target_index]["values"][left_group]["Adjust"] - records[target_index]["values"][right_group]["Adjust"]
    wrong_subheader = records[target_index]["values"][right_group]["Base"] - records[target_index]["values"][left_group]["Base"]
    distractors = unique_distractors(
        gold,
        [
            ("wrong_header", wrong_header),
            ("wrong_subheader", wrong_subheader),
            ("flat_header_skip", flat_adjust),
            ("exception_skip", raw_delta),
        ],
    )
    nav_tier = "A" if level == 1 else "B" if level == 2 else "C"
    floor = 8 if level == 1 else 18 if level == 2 else 34
    evidence = [
        evidence_cell(1, 1, "header"),
        evidence_cell(target_index + 3, 0, "target"),
        evidence_cell(1, 1 + len(subheaders), "header"),
        evidence_cell(target_index + 3, 2, "target"),
        evidence_cell(note_row, 4, "exception") if level == 3 else evidence_cell(2, 2, "rule"),
    ]
    contract = action_contract(nav_tier, floor, evidence, estimated_human_mean_actions=42 + level * 14, estimated_human_second_best_actions=30 + level * 10)
    metadata = v3_metadata(
        template_id="merged_group_header_delta",
        skill_ids=["merged_cells"],
        level=level,
        nav_tier=nav_tier,
        answer_form="number",
        visual_extensions_used=["mergeRanges", "viewportMeta"],
        action_contract=contract,
        gold_evidence_path=evidence,
        shortcut_traps=[item["trap_id"] for item in distractors],
        distractor_derivations=distractors,
        primary_failure_modes=["header_resolution", "subheader_alignment", "exception_handling"],
        required_visible_evidence=[target_label, left_group, right_group, "Adjust"],
        hidden_program_shape="target row lookup -> resolve merged group/subheader pairs -> compute right-left delta -> optional note multiplier",
        extras={
            "merge_ranges": [
                {"sheet_id": "main", "start_row": 1, "start_col": 1 + i * 3, "row_span": 1, "col_span": 3, "text": group, "role": "column_group", "internal_grid_hidden": True}
                for i, group in enumerate(groups)
            ],
            "target_row_label": target_label,
            "target_status": target_status,
        },
    )
    return _common_task(
        task_id=f"merged_group_header_delta_l{level}_{seed:06d}",
        seed=seed,
        question=f"{target_label} 행에서 {right_group}의 Adjust 값과 {left_group}의 Adjust 값 차이를 WORKBOOK NOTE 규칙까지 적용해 제출하세요.",
        answer=gold,
        answer_type="integer",
        table=rows,
        tags=["merged_cells", "merged_group_header_delta", "hierarchical_header", "numerical_delta"],
        max_actions=180 if level < 3 else 240,
        human_mean_actions=contract["estimated_human_mean_actions"],
        human_second_best_actions=contract["estimated_human_second_best_actions"],
        private_metadata=metadata,
    )


def generate_cell_icon_legend_count_task(seed: int = 0, level: int = 2) -> TaskSpec:
    if level not in {1, 2, 3}:
        raise ValueError("level must be 1, 2, or 3")
    rng = _rng(seed, level, 2_000)
    shapes = ["circle", "triangle", "diamond", "hex"]
    patterns = ["solid", "outline", "dots", "slash"]
    icons = [(shape, pattern, f"{shape[:2].upper()}-{pattern[:2].upper()}") for shape in shapes for pattern in patterns]
    rng.shuffle(icons)
    target_shape, target_pattern, target_icon = icons[0]
    shape_decoy = next(icon for icon in icons[1:] if icon[0] == target_shape)
    row_count = 8 + level * 4
    threshold = 20 + level * 3

    rows: list[list[Cell]] = [_page("ICON DATA PAGE")]
    rows.append([_header("CODE"), _header("ICON"), _header("PLANNED"), _header("CONFIRMED"), _header("STATUS"), Cell("")])
    records: list[dict[str, Any]] = []
    for idx in range(row_count):
        icon = rng.choice(icons[:6])
        confirmed = rng.randint(8, 44)
        rec = {
            "code": _token(rng, "IC", 2),
            "icon": icon,
            "planned": confirmed + rng.randint(2, 13),
            "confirmed": confirmed,
            "status": rng.choice(["KEEP", "PASS", "HOLD"]),
        }
        records.append(rec)
    for idx in rng.sample(range(row_count), max(2, level + 1)):
        records[idx]["icon"] = (target_shape, target_pattern, target_icon)
        records[idx]["confirmed"] = max(threshold + 1, records[idx]["confirmed"])
    if level == 3:
        records[rng.randrange(row_count)]["status"] = "HOLD"

    gold_rows = [
        rec
        for rec in records
        if rec["icon"][2] == target_icon and (level < 3 or rec["confirmed"] >= threshold) and rec["status"] != "HOLD"
    ]
    gold = sum(int(rec["confirmed"]) for rec in gold_rows)
    for rec in records:
        shape, pattern, icon_id = rec["icon"]
        rows.append(
            [
                Cell(rec["code"]),
                Cell(""),
                Cell(str(rec["planned"])),
                Cell(str(rec["confirmed"])),
                Cell(rec["status"]),
                Cell(""),
            ]
        )

    legend_start = len(rows) + 2
    rows.append(_blank(6))
    rows.append(_page("ICON LEGEND PAGE"))
    rows.append([_header("TYPE"), _header("ICON"), _header("SHAPE"), _header("PATTERN"), _header("RULE"), Cell("")])
    rows.append([Cell("TYPE R"), Cell(""), Cell(target_shape), Cell(target_pattern), Cell(f"CONF >= {threshold}" if level == 3 else "CONF SUM"), Cell("")])
    rows.append([Cell("TYPE Q"), Cell(""), Cell(shape_decoy[0]), Cell(shape_decoy[1]), Cell("DECOY"), Cell("")])

    shape_only = sum(int(rec["confirmed"]) for rec in records if rec["icon"][0] == target_shape and rec["status"] != "HOLD")
    most_common_icon = records[0]["icon"][2]
    legend_skip = sum(int(rec["confirmed"]) for rec in records if rec["icon"][2] == most_common_icon)
    wrong_column = sum(int(rec["planned"]) for rec in gold_rows)
    distractors = unique_distractors(
        gold,
        [
            ("shape_only_confusion", shape_only),
            ("legend_skip", legend_skip),
            ("wrong_column", wrong_column),
            ("exception_skip", sum(int(rec["confirmed"]) for rec in records if rec["icon"][2] == target_icon)),
        ],
    )
    nav_tier = "A" if level == 1 else "B" if level == 2 else "C"
    floor = 9 if level == 1 else 20 if level == 2 else 36
    required_pages = ["data", "legend"] if level >= 2 else None
    evidence = [
        evidence_cell(1, 1, "target", page_id="data"),
        evidence_cell(legend_start + 1, 1, "legend", page_id="legend"),
        evidence_cell(legend_start + 1, 4, "rule", page_id="legend"),
    ]
    contract = action_contract(nav_tier, floor, evidence, required_page_sequence=required_pages, estimated_human_mean_actions=36 + level * 16, estimated_human_second_best_actions=24 + level * 11)
    metadata = v3_metadata(
        template_id="cell_icon_legend_count",
        skill_ids=["cell_media"],
        level=level,
        nav_tier=nav_tier,
        answer_form="number",
        visual_extensions_used=["cellMedia", "pageGraph", "viewportMeta"],
        action_contract=contract,
        gold_evidence_path=evidence,
        shortcut_traps=[item["trap_id"] for item in distractors],
        distractor_derivations=distractors,
        primary_failure_modes=["icon_matching", "legend_lookup", "conditional_sum"],
        required_visible_evidence=["TYPE R", target_shape, target_pattern],
        hidden_program_shape="lookup target icon in legend -> filter matching data icons -> optional threshold/status rule -> sum confirmed metric",
        extras={
            "cell_media": [
                {"type": "icon", "sheet_id": "main", "row": i + 2, "col": 1, "icon_id": rec["icon"][2], "shape": rec["icon"][0], "pattern": rec["icon"][1]}
                for i, rec in enumerate(records)
            ]
            + [
                {"type": "icon", "sheet_id": "main", "row": legend_start + 2, "col": 1, "icon_id": target_icon, "shape": target_shape, "pattern": target_pattern},
                {"type": "icon", "sheet_id": "main", "row": legend_start + 3, "col": 1, "icon_id": shape_decoy[2], "shape": shape_decoy[0], "pattern": shape_decoy[1]},
            ],
            "page_graph": {
                "start_page_id": "data",
                "pages": [
                    {"page_id": "data", "label": "ICON DATA PAGE", "role": "main_table", "order": 1},
                    {"page_id": "legend", "label": "ICON LEGEND PAGE", "role": "legend", "order": 2},
                ],
                "required_page_sequence": required_pages or ["data"],
                "decoy_pages": [],
            },
        },
    )
    return _common_task(
        task_id=f"cell_icon_legend_count_l{level}_{seed:06d}",
        seed=seed,
        question="ICON LEGEND PAGE에서 TYPE R의 shape/pattern을 확인한 뒤, ICON DATA PAGE에서 해당 icon 행의 CONFIRMED 합계를 제출하세요.",
        answer=gold,
        answer_type="integer",
        table=rows,
        tags=["cell_media", "cell_icon_legend_count", "icon_legend", "aggregation"],
        max_actions=180 if level < 3 else 260,
        human_mean_actions=contract["estimated_human_mean_actions"],
        human_second_best_actions=contract["estimated_human_second_best_actions"],
        private_metadata=metadata,
    )


def generate_massive_sparse_anchor_lookup_task(seed: int = 0, level: int = 2) -> TaskSpec:
    if level not in {1, 2, 3}:
        raise ValueError("level must be 1, 2, or 3")
    rng = _rng(seed, level, 3_000)
    n_rows = 40 if level == 1 else 80 if level == 2 else 120
    n_groups = 5 if level == 1 else 8 if level == 2 else 10
    subheaders = ["V1", "V2", "V3"]
    groups = [f"Group {name}" for name in rng.sample(list("ABCDEFGHJKLMNPQRSTUVWXYZ"), n_groups)]
    target_group = groups[-2]
    target_sub = rng.choice(subheaders)
    target_row = n_rows - rng.randint(5, 12)
    target_code = _token(rng, "R7Q", 2)

    width = 1 + n_groups * len(subheaders)
    rows: list[list[Cell]] = [[_header("MASSIVE GRID"), *_blank(width - 1)]]
    rows.append([_header("CODE"), *[Cell(group, bg="#dbeafe", bold=True) for group in groups for _ in subheaders]])
    rows.append([_header("CODE"), *[_header(sub) for _ in groups for sub in subheaders]])

    target_col = 1 + groups.index(target_group) * len(subheaders) + subheaders.index(target_sub)
    answer = _token(rng, "VAL", 2)
    near_code = target_code[::-1].replace("Q7R", "R7Q")
    for ridx in range(n_rows):
        code = target_code if ridx == target_row else near_code if ridx == target_row - 1 else _token(rng, "R7Q", 2)
        row = [Cell(code)]
        for col in range(1, width):
            value = answer if ridx == target_row and col == target_col else _token(rng, "V", 2)
            row.append(Cell(value))
        rows.append(row)

    wrong_group_value = rows[target_row + 3][max(1, target_col - len(subheaders))].text
    near_value = rows[target_row + 2][target_col].text
    top_left_value = rows[4][2].text
    distractors = unique_distractors(
        answer,
        [
            ("near_code_confusion", near_value),
            ("wrong_column_group", wrong_group_value),
            ("top_left_bias", top_left_value),
            ("wrong_submetric", rows[target_row + 3][target_col - 1].text),
        ],
    )
    nav_tier = "B" if level == 1 else "C" if level == 2 else "D"
    floor = 20 if level == 1 else 44 if level == 2 else 72
    evidence = [
        evidence_cell(target_row + 3, 0, "target"),
        evidence_cell(1, target_col, "header"),
        evidence_cell(2, target_col, "header"),
        evidence_cell(target_row + 3, target_col, "target"),
    ]
    contract = action_contract(nav_tier, floor, evidence, action_model="viewport_step", estimated_human_mean_actions=70 + level * 35, estimated_human_second_best_actions=48 + level * 24)
    metadata = v3_metadata(
        template_id="massive_sparse_anchor_lookup",
        skill_ids=["massive_tables"],
        level=level,
        nav_tier=nav_tier,
        answer_form="cell_value",
        visual_extensions_used=["viewportMeta", "mergeRanges"],
        action_contract=contract,
        gold_evidence_path=evidence,
        shortcut_traps=[item["trap_id"] for item in distractors],
        distractor_derivations=distractors,
        primary_failure_modes=["large_grid_navigation", "row_anchor", "column_anchor"],
        required_visible_evidence=[target_code, target_group, target_sub],
        hidden_program_shape="locate far row code -> resolve grouped column/submetric -> read intersection cell",
        extras={
            "merge_ranges": [
                {"sheet_id": "main", "start_row": 1, "start_col": 1 + i * 3, "row_span": 1, "col_span": 3, "text": group, "role": "column_group", "internal_grid_hidden": True}
                for i, group in enumerate(groups)
            ],
            "viewport_meta": {"start_cell": {"row": 0, "col": 0}, "total_rows": len(rows), "total_cols": width, "target_visible_at_reset": False},
        },
    )
    return _common_task(
        task_id=f"massive_sparse_anchor_lookup_l{level}_{seed:06d}",
        seed=seed,
        question=f"Code가 {target_code}인 행에서 {target_group} 아래 {target_sub} 셀 값을 제출하세요.",
        answer=answer,
        answer_type="string",
        table=rows,
        tags=["massive_tables", "massive_sparse_anchor_lookup", "large_grid_navigation", "row_anchor"],
        max_actions=260 if level == 1 else 420 if level == 2 else 620,
        human_mean_actions=contract["estimated_human_mean_actions"],
        human_second_best_actions=contract["estimated_human_second_best_actions"],
        private_metadata=metadata,
    )


def generate_multipage_index_rule_lookup_task(seed: int = 0, level: int = 2) -> TaskSpec:
    if level not in {1, 2, 3}:
        raise ValueError("level must be 1, 2, or 3")
    rng = _rng(seed, level, 4_000)
    target_code = _token(rng, "MP", 2)
    metric = rng.choice(["BASE", "LOAD", "COUNT"])
    data_page = rng.choice(["DATA-A", "DATA-B", "DATA-C"])
    rule_delta = rng.randint(5, 18)
    raw = rng.randint(40, 90)
    exception_delta = rng.randint(3, 9) if level == 3 else 0
    gold = raw + rule_delta - exception_delta

    rows: list[list[Cell]] = [_page("QUERY PAGE")]
    rows.append([_header("QUERY"), Cell("CODE"), Cell(target_code), Cell("METRIC"), Cell(metric), Cell("")])
    rows.append(_blank(6))
    rows.append(_page("INDEX PAGE"))
    rows.append([_header("CODE"), _header("PAGE"), _header("NOTE"), Cell(""), Cell(""), Cell("")])
    for page in ["DATA-A", "DATA-B", "DATA-C"]:
        code = target_code if page == data_page else _token(rng, "MP", 2)
        rows.append([Cell(code), Cell(page), Cell("ACTIVE" if page == data_page else "DECOY"), Cell(""), Cell(""), Cell("")])
    rows.append(_blank(6))
    rule_row = len(rows) + 1
    rows.append(_page("RULE PAGE"))
    rows.append([_header("METRIC"), _header("OP"), _header("AMOUNT"), Cell(""), Cell(""), Cell("")])
    rows.append([Cell(metric), Cell("ADD"), Cell(str(rule_delta)), Cell(""), Cell(""), Cell("")])
    if level == 3:
        rows.append([Cell("EXCEPTION"), Cell("SUBTRACT"), Cell(str(exception_delta)), Cell(""), Cell(""), Cell("")])
    rows.append(_blank(6))
    data_start = len(rows)
    for page in ["DATA-A", "DATA-B", "DATA-C"]:
        rows.append(_page(page))
        rows.append([_header("CODE"), _header(metric), _header("ALT"), Cell(""), Cell(""), Cell("")])
        page_raw = raw if page == data_page else raw + rng.randint(11, 25)
        rows.append([Cell(target_code), Cell(str(page_raw)), Cell(str(page_raw + 4)), Cell(""), Cell(""), Cell("")])

    rule_skip = raw
    wrong_page = raw + 12
    index_skip = raw + rule_delta + 8
    distractors = unique_distractors(
        gold,
        [
            ("index_skip", index_skip),
            ("rule_skip", rule_skip),
            ("wrong_page", wrong_page),
            ("exception_skip", raw + rule_delta),
        ],
    )
    nav_tier = "B" if level == 1 else "C"
    floor = 18 if level == 1 else 36 if level == 2 else 52
    sequence = ["query", "index", "rule", data_page.lower()]
    if level == 3:
        sequence.insert(3, "exception")
    evidence = [
        evidence_cell(1, 2, "query", page_id="query"),
        evidence_cell(4, 1, "target", page_id="index"),
        evidence_cell(rule_row + 1, 2, "rule", page_id="rule"),
        evidence_cell(data_start + 2, 1, "target", page_id=data_page.lower()),
    ]
    contract = action_contract(nav_tier, floor, evidence, required_page_sequence=sequence, action_model="page_jump", estimated_human_mean_actions=58 + level * 22, estimated_human_second_best_actions=40 + level * 15)
    metadata = v3_metadata(
        template_id="multipage_index_rule_lookup",
        skill_ids=["multi_page"],
        level=level,
        nav_tier=nav_tier,
        answer_form="number",
        visual_extensions_used=["pageGraph", "viewportMeta"],
        action_contract=contract,
        gold_evidence_path=evidence,
        shortcut_traps=[item["trap_id"] for item in distractors],
        distractor_derivations=distractors,
        primary_failure_modes=["page_navigation", "index_lookup", "rule_transfer"],
        required_visible_evidence=[target_code, data_page, metric, str(rule_delta)],
        hidden_program_shape="query -> index page -> rule page -> data page -> apply rule and optional exception",
        extras={
            "page_graph": {
                "start_page_id": "query",
                "pages": [
                    {"page_id": "query", "label": "QUERY PAGE", "role": "query", "order": 1},
                    {"page_id": "index", "label": "INDEX PAGE", "role": "index", "order": 2},
                    {"page_id": "rule", "label": "RULE PAGE", "role": "rule", "order": 3},
                    {"page_id": data_page.lower(), "label": data_page, "role": "main_table", "order": 4},
                ],
                "required_page_sequence": sequence,
                "decoy_pages": ["data-a", "data-b", "data-c"],
            }
        },
    )
    return _common_task(
        task_id=f"multipage_index_rule_lookup_l{level}_{seed:06d}",
        seed=seed,
        question=f"QUERY PAGE의 {target_code}/{metric} 요청을 INDEX PAGE와 RULE PAGE를 이용해 계산한 최종 수치를 제출하세요.",
        answer=gold,
        answer_type="integer",
        table=rows,
        tags=["multi_page", "multipage_index_rule_lookup", "page_navigation", "rule_transfer"],
        max_actions=260 if level == 1 else 420,
        human_mean_actions=contract["estimated_human_mean_actions"],
        human_second_best_actions=contract["estimated_human_second_best_actions"],
        private_metadata=metadata,
    )


def generate_compound_merged_symbol_multipage_task(seed: int = 0, level: int = 2) -> TaskSpec:
    if level not in {1, 2, 3}:
        raise ValueError("level must be 1, 2, or 3")
    rng = _rng(seed, level, 5_000)
    groups = [f"Band {name}" for name in rng.sample(["A", "B", "C"], 3)]
    subheaders = ["Raw", "Adj"]
    symbols = rng.sample(_SYMBOLS, 3)
    target_label = _token(rng, "CM", 2)
    target_group = groups[1]
    target_symbol = symbols[0]
    rule = rng.choice([f"+{rng.randint(5, 12)}", f"-{rng.randint(3, 9)}", f"x{rng.randint(2, 3)}"])
    base_value = rng.randint(18, 44)
    token = f"{base_value}{target_symbol}"
    before_exception = _apply_rule(rule, base_value)
    exception_amount = rng.randint(4, 10) if level == 3 else 0
    gold = before_exception + exception_amount

    rows: list[list[Cell]] = [_page("MAIN PAGE")]
    rows.append([_header("ITEM"), *[Cell(group, bg="#dbeafe", bold=True) for group in groups for _ in subheaders]])
    rows.append([_header("ITEM"), *[_header(sub) for _ in groups for sub in subheaders]])
    target_row = rng.randrange(3, 9)
    target_col = 1 + groups.index(target_group) * len(subheaders) + subheaders.index("Adj")
    for ridx in range(9):
        label = target_label if ridx == target_row else _token(rng, "CM", 2)
        row = [Cell(label, bg="#fef9c3" if label == target_label else "#ffffff")]
        for group in groups:
            row.append(Cell(str(rng.randint(10, 55))))
            row.append(Cell(f"{rng.randint(10, 55)}{rng.choice(symbols)}"))
        row[target_col] = Cell(token, bg="#fef9c3")
        rows.append(row)
    rows.append(_blank(7))
    legend_start = len(rows)
    rows.append(_page("LEGEND PAGE"))
    rows.append([_header("GLYPH"), _header("OP"), _header("SCOPE"), Cell(""), Cell(""), Cell(""), Cell("")])
    rows.append([Cell(target_symbol), Cell(rule), Cell(target_group), Cell(""), Cell(""), Cell(""), Cell("")])
    for sym in symbols[1:]:
        rows.append([Cell(sym), Cell(f"+{rng.randint(1, 4)}"), Cell("DECOY"), Cell(""), Cell(""), Cell(""), Cell("")])
    if level == 3:
        rows.append(_blank(7))
        rows.append(_page("EXCEPTION PAGE"))
        rows.append([_header("GROUP"), _header("OP"), _header("AMOUNT"), Cell(""), Cell(""), Cell(""), Cell("")])
        rows.append([Cell(target_group), Cell("ADD"), Cell(str(exception_amount)), Cell(""), Cell(""), Cell(""), Cell("")])

    sibling_token = rows[target_row + 3][target_col - 2].text
    sibling_value, sibling_symbol = _parse_token(sibling_token) if any(ch in sibling_token for ch in _SYMBOLS) else (int(sibling_token), target_symbol)
    distractors = unique_distractors(
        gold,
        [
            ("merged_header_skip", _apply_rule(rule, sibling_value)),
            ("symbol_ignore", base_value),
            ("page_skip", base_value + 1),
            ("exception_skip", before_exception),
        ],
    )
    nav_tier = "B" if level == 1 else "C" if level == 2 else "D"
    floor = 22 if level == 1 else 44 if level == 2 else 72
    sequence = ["main", "legend"] if level < 3 else ["main", "legend", "exception"]
    evidence = [
        evidence_cell(target_row + 3, 0, "target", page_id="main"),
        evidence_cell(1, target_col, "header", page_id="main"),
        evidence_cell(target_row + 3, target_col, "target", page_id="main"),
        evidence_cell(legend_start + 2, 1, "legend", page_id="legend"),
    ]
    if level == 3:
        evidence.append(evidence_cell(len(rows) - 1, 2, "exception", page_id="exception"))
    contract = action_contract(nav_tier, floor, evidence, required_page_sequence=sequence, action_model="mixed", estimated_human_mean_actions=68 + level * 34, estimated_human_second_best_actions=48 + level * 22)
    metadata = v3_metadata(
        template_id="compound_merged_symbol_multipage",
        skill_ids=["merged_cells", "symbolic_cells", "multi_page", "composed_stressors"],
        level=level,
        nav_tier=nav_tier,
        answer_form="number",
        visual_extensions_used=["mergeRanges", "pageGraph", "viewportMeta"],
        action_contract=contract,
        gold_evidence_path=evidence,
        shortcut_traps=[item["trap_id"] for item in distractors],
        distractor_derivations=distractors,
        primary_failure_modes=["header_resolution", "legend_lookup", "exception_handling"],
        required_visible_evidence=[target_label, target_group, "Adj", target_symbol, rule],
        hidden_program_shape="resolve merged header -> parse numeric+symbol target cell -> read legend page -> apply symbol rule -> optional exception page",
        diagnostics_extra={
            "skill_components": ["merged_cells", "symbolic_cells", "multi_page"],
            "ablation_variants": {
                "no_merged": "symbol_legend_cross_sheet",
                "no_symbol": "merged_group_header_delta",
                "no_page": "symbol_adjusted_score",
            },
        },
        extras={
            "merge_ranges": [
                {"sheet_id": "main", "start_row": 1, "start_col": 1 + i * 2, "row_span": 1, "col_span": 2, "text": group, "role": "column_group", "internal_grid_hidden": True}
                for i, group in enumerate(groups)
            ],
            "page_graph": {
                "start_page_id": "main",
                "pages": [
                    {"page_id": "main", "label": "MAIN PAGE", "role": "main_table", "order": 1},
                    {"page_id": "legend", "label": "LEGEND PAGE", "role": "legend", "order": 2},
                    {"page_id": "exception", "label": "EXCEPTION PAGE", "role": "exception", "order": 3},
                ],
                "required_page_sequence": sequence,
                "decoy_pages": [],
            },
            "symbol_rules": {target_symbol: rule},
            "sibling_symbol": sibling_symbol,
        },
    )
    return _common_task(
        task_id=f"compound_merged_symbol_multipage_l{level}_{seed:06d}",
        seed=seed,
        question=f"{target_label} 행에서 {target_group}의 Adj 토큰을 읽고 LEGEND PAGE와 필요한 예외 규칙을 적용한 최종 수치를 제출하세요.",
        answer=gold,
        answer_type="integer",
        table=rows,
        tags=["composed_stressors", "compound_merged_symbol_multipage", "merged_cells", "symbolic_cells", "multi_page"],
        max_actions=320 if level == 1 else 520 if level == 2 else 760,
        human_mean_actions=contract["estimated_human_mean_actions"],
        human_second_best_actions=contract["estimated_human_second_best_actions"],
        private_metadata=metadata,
    )


def generate_v3_task(task_family: str, seed: int = 0, level: int = 2) -> TaskSpec:
    generators = {
        "merged_group_header_delta": generate_merged_group_header_delta_task,
        "cell_icon_legend_count": generate_cell_icon_legend_count_task,
        "massive_sparse_anchor_lookup": generate_massive_sparse_anchor_lookup_task,
        "multipage_index_rule_lookup": generate_multipage_index_rule_lookup_task,
        "compound_merged_symbol_multipage": generate_compound_merged_symbol_multipage_task,
    }
    try:
        return generators[task_family](seed=seed, level=level)
    except KeyError as exc:
        raise ValueError(f"unknown v3 task family: {task_family}") from exc


__all__ = [
    "V3_TASK_FAMILIES",
    "generate_cell_icon_legend_count_task",
    "generate_compound_merged_symbol_multipage_task",
    "generate_massive_sparse_anchor_lookup_task",
    "generate_merged_group_header_delta_task",
    "generate_multipage_index_rule_lookup_task",
    "generate_v3_task",
    "validate_v3_task",
]
