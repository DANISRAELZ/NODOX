from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


FIGURE_SPECS = [
    {
        "name": "figure_1_top_candidates_meta_priority",
        "title": "Top Candidates by Meta Priority",
        "source": "publication_table_1_top_candidates.csv",
        "columns": ["gene", "protein_id", "meta_priority_score"],
        "kind": "horizontal_bar",
        "x": "meta_priority_score",
    },
    {
        "name": "figure_2_priority_vs_confidence",
        "title": "Therapeutic Priority vs Evidence Confidence",
        "source": "publication_table_1_top_candidates.csv",
        "columns": ["gene", "protein_id", "therapeutic_priority_score", "evidence_confidence_score"],
        "kind": "scatter",
        "x": "therapeutic_priority_score",
        "y": "evidence_confidence_score",
    },
    {
        "name": "figure_3_score_decomposition",
        "title": "Score Decomposition by Candidate",
        "source": "publication_table_2_score_decomposition.csv",
        "columns": [
            "gene",
            "protein_id",
            "therapeutic_priority_score",
            "evidence_confidence_score",
            "functional_node_score",
            "evolutionary_escape_risk_score",
        ],
        "kind": "grouped_bar",
    },
    {
        "name": "figure_4_evolutionary_risk_vs_priority",
        "title": "Evolutionary Risk vs Therapeutic Priority",
        "source": "publication_table_1_top_candidates.csv",
        "columns": ["gene", "protein_id", "evolutionary_escape_risk_score", "therapeutic_priority_score"],
        "kind": "scatter",
        "x": "evolutionary_escape_risk_score",
        "y": "therapeutic_priority_score",
    },
    {
        "name": "figure_5_ranking_stability",
        "title": "Ranking Stability by Candidate",
        "source": "publication_table_4_sensitivity_stability.csv",
        "columns": ["protein_id", "rank_delta_vs_base"],
        "kind": "stability_bar",
    },
    {
        "name": "figure_6_therapeutic_role_distribution",
        "title": "Therapeutic Role Distribution",
        "source": "publication_table_1_top_candidates.csv",
        "columns": ["therapeutic_role"],
        "kind": "role_bar",
    },
]


PALETTE = ["#3B7EA1", "#E57C23", "#5B8E7D", "#C8553D", "#6A5ACD", "#687076"]
TEXT = "#1F2933"
GRID = "#D7DEE8"
BACKGROUND = "#FFFFFF"


def build_publication_figures(
    publication_package_dir: Path | str = "results/publication_package",
    output_dir: Path | str = "results/publication_package/figures",
) -> list[dict[str, object]]:
    package_dir = Path(publication_package_dir)
    figures_dir = Path(output_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    generated: list[dict[str, object]] = []
    for spec in FIGURE_SPECS:
        source_path = package_dir / str(spec["source"])
        if not source_path.exists():
            generated.append(_skipped(spec, f"Missing source file: {source_path.name}"))
            continue
        data = pd.read_csv(source_path)
        missing = [column for column in spec["columns"] if column not in data.columns]
        if missing:
            generated.append(_skipped(spec, "Missing required columns: " + ", ".join(missing)))
            continue
        prepared = _prepare_data(data, spec)
        if prepared.empty:
            generated.append(_skipped(spec, "No plottable rows after numeric cleaning."))
            continue
        png_path = figures_dir / f"{spec['name']}.png"
        svg_path = figures_dir / f"{spec['name']}.svg"
        _draw_png(prepared, spec, png_path)
        _draw_svg(prepared, spec, svg_path)
        generated.append(
            {
                "figure": spec["name"],
                "title": spec["title"],
                "source_file": spec["source"],
                "png": png_path.name,
                "svg": svg_path.name,
                "status": "generated",
                "note": "Generated from consolidated local publication tables.",
            }
        )

    _write_interpretation(figures_dir, generated)
    return generated


def _prepare_data(data: pd.DataFrame, spec: dict[str, object]) -> pd.DataFrame:
    kind = str(spec["kind"])
    prepared = data.copy()
    if kind == "horizontal_bar":
        prepared[str(spec["x"])] = pd.to_numeric(prepared[str(spec["x"])], errors="coerce")
        return prepared.dropna(subset=[str(spec["x"])]).sort_values(str(spec["x"]), ascending=False).head(10)
    if kind == "scatter":
        prepared[str(spec["x"])] = pd.to_numeric(prepared[str(spec["x"])], errors="coerce")
        prepared[str(spec["y"])] = pd.to_numeric(prepared[str(spec["y"])], errors="coerce")
        return prepared.dropna(subset=[str(spec["x"]), str(spec["y"])]).head(12)
    if kind == "grouped_bar":
        value_columns = [
            "therapeutic_priority_score",
            "evidence_confidence_score",
            "functional_node_score",
            "evolutionary_escape_risk_score",
        ]
        for column in value_columns:
            prepared[column] = pd.to_numeric(prepared[column], errors="coerce")
        return prepared.dropna(subset=value_columns, how="all").head(8)
    if kind == "stability_bar":
        prepared["rank_delta_vs_base"] = pd.to_numeric(prepared["rank_delta_vs_base"], errors="coerce")
        prepared = prepared.dropna(subset=["rank_delta_vs_base"])
        if prepared.empty:
            return prepared
        grouped = (
            prepared.assign(abs_rank_delta=prepared["rank_delta_vs_base"].abs())
            .groupby("protein_id", as_index=False)
            .agg(max_abs_rank_delta=("abs_rank_delta", "max"))
            .sort_values(["max_abs_rank_delta", "protein_id"], ascending=[False, True])
            .head(12)
        )
        return grouped
    if kind == "role_bar":
        return (
            prepared["therapeutic_role"]
            .fillna("not_reported")
            .astype(str)
            .value_counts()
            .rename_axis("therapeutic_role")
            .reset_index(name="candidate_count")
        )
    return pd.DataFrame()


def _draw_png(data: pd.DataFrame, spec: dict[str, object], path: Path) -> None:
    image = Image.new("RGB", (1100, 720), BACKGROUND)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()
    draw.text((40, 28), str(spec["title"]), fill=TEXT, font=title_font)
    draw.text((40, 52), "Computational demonstration; interpret with provenance and confidence limits.", fill="#52616B", font=font)
    kind = str(spec["kind"])
    if kind == "horizontal_bar":
        _draw_horizontal_bar(draw, data, label_column=_label_column(data), value_column=str(spec["x"]), area=(260, 100, 1040, 650), font=font)
    elif kind == "scatter":
        _draw_scatter(draw, data, x_column=str(spec["x"]), y_column=str(spec["y"]), area=(110, 105, 1010, 620), font=font)
    elif kind == "grouped_bar":
        _draw_grouped_bar(draw, data, area=(90, 105, 1040, 620), font=font)
    elif kind == "stability_bar":
        _draw_horizontal_bar(draw, data, label_column="protein_id", value_column="max_abs_rank_delta", area=(260, 100, 1040, 650), font=font)
    elif kind == "role_bar":
        _draw_horizontal_bar(draw, data, label_column="therapeutic_role", value_column="candidate_count", area=(330, 100, 1040, 650), font=font)
    image.save(path)


def _draw_svg(data: pd.DataFrame, spec: dict[str, object], path: Path) -> None:
    bars = []
    kind = str(spec["kind"])
    if kind in {"horizontal_bar", "stability_bar", "role_bar"}:
        label_column = _label_column(data) if kind == "horizontal_bar" else ("protein_id" if kind == "stability_bar" else "therapeutic_role")
        value_column = str(spec.get("x", "max_abs_rank_delta")) if kind == "horizontal_bar" else ("max_abs_rank_delta" if kind == "stability_bar" else "candidate_count")
        max_value = max(float(data[value_column].max()), 1.0)
        y = 95
        for idx, row in data.iterrows():
            value = float(row[value_column])
            width = int((value / max_value) * 680)
            label = _xml(str(row[label_column]))
            color = PALETTE[int(idx) % len(PALETTE)]
            bars.append(f'<text x="30" y="{y + 18}" font-size="12" fill="{TEXT}">{label}</text>')
            bars.append(f'<rect x="300" y="{y}" width="{width}" height="24" fill="{color}"/>')
            bars.append(f'<text x="{310 + width}" y="{y + 18}" font-size="12" fill="{TEXT}">{value:.3g}</text>')
            y += 36
    else:
        bars.append('<text x="40" y="120" font-size="14" fill="#52616B">See PNG for labeled point layout.</text>')
    svg = "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="720" viewBox="0 0 1100 720">',
            f'<rect width="1100" height="720" fill="{BACKGROUND}"/>',
            f'<text x="40" y="40" font-size="20" fill="{TEXT}">{_xml(str(spec["title"]))}</text>',
            '<text x="40" y="64" font-size="12" fill="#52616B">Computational demonstration; interpret with provenance and confidence limits.</text>',
            *bars,
            "</svg>",
        ]
    )
    path.write_text(svg, encoding="utf-8")


def _draw_horizontal_bar(
    draw: ImageDraw.ImageDraw,
    data: pd.DataFrame,
    label_column: str,
    value_column: str,
    area: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
) -> None:
    left, top, right, bottom = area
    max_value = max(float(data[value_column].max()), 1.0)
    bar_height = max(18, min(34, int((bottom - top) / max(len(data), 1) * 0.55)))
    gap = max(10, int((bottom - top) / max(len(data), 1) * 0.35))
    for idx, (_, row) in enumerate(data.iterrows()):
        y = top + idx * (bar_height + gap)
        value = float(row[value_column])
        width = int((value / max_value) * (right - left))
        label = _short_label(row[label_column])
        draw.text((40, y + 5), label, fill=TEXT, font=font)
        draw.rectangle((left, y, right, y + bar_height), outline=GRID)
        draw.rectangle((left, y, left + width, y + bar_height), fill=PALETTE[idx % len(PALETTE)])
        draw.text((left + width + 8, y + 4), f"{value:.3g}", fill=TEXT, font=font)


def _draw_scatter(
    draw: ImageDraw.ImageDraw,
    data: pd.DataFrame,
    x_column: str,
    y_column: str,
    area: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
) -> None:
    left, top, right, bottom = area
    draw.rectangle(area, outline=TEXT)
    for tick in range(0, 6):
        x = left + int((right - left) * tick / 5)
        y = bottom - int((bottom - top) * tick / 5)
        draw.line((x, top, x, bottom), fill=GRID)
        draw.line((left, y, right, y), fill=GRID)
        draw.text((x - 8, bottom + 8), f"{tick / 5:.1f}", fill=TEXT, font=font)
        draw.text((left - 38, y - 6), f"{tick / 5:.1f}", fill=TEXT, font=font)
    draw.text((left, bottom + 32), x_column, fill=TEXT, font=font)
    draw.text((left - 60, top - 22), y_column, fill=TEXT, font=font)
    for idx, (_, row) in enumerate(data.iterrows()):
        x_value = max(0.0, min(1.0, float(row[x_column])))
        y_value = max(0.0, min(1.0, float(row[y_column])))
        x = left + int((right - left) * x_value)
        y = bottom - int((bottom - top) * y_value)
        color = PALETTE[idx % len(PALETTE)]
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=color, outline=TEXT)
        draw.text((x + 8, y - 8), _short_label(row[_label_column(data)], 18), fill=TEXT, font=font)


def _draw_grouped_bar(
    draw: ImageDraw.ImageDraw,
    data: pd.DataFrame,
    area: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
) -> None:
    value_columns = [
        "therapeutic_priority_score",
        "evidence_confidence_score",
        "functional_node_score",
        "evolutionary_escape_risk_score",
    ]
    left, top, right, bottom = area
    draw.rectangle(area, outline=TEXT)
    group_width = max(70, int((right - left) / max(len(data), 1)))
    bar_width = max(8, int(group_width / (len(value_columns) + 2)))
    for idx, (_, row) in enumerate(data.iterrows()):
        base_x = left + idx * group_width + 10
        draw.text((base_x, bottom + 8), _short_label(row[_label_column(data)], 12), fill=TEXT, font=font)
        for col_idx, column in enumerate(value_columns):
            value = float(pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").fillna(0.0).iloc[0])
            height = int((bottom - top - 30) * max(0.0, min(1.0, value)))
            x0 = base_x + col_idx * bar_width
            y0 = bottom - height
            draw.rectangle((x0, y0, x0 + bar_width - 2, bottom), fill=PALETTE[col_idx])
    legend_x = right - 360
    for col_idx, column in enumerate(value_columns):
        y = top + col_idx * 22
        draw.rectangle((legend_x, y, legend_x + 12, y + 12), fill=PALETTE[col_idx])
        draw.text((legend_x + 18, y - 1), column, fill=TEXT, font=font)


def _write_interpretation(figures_dir: Path, generated: list[dict[str, object]]) -> None:
    lines = [
        "# Publication Figures Interpretation",
        "",
        "These figures are reproducible computational demonstration outputs. They help inspect candidate functional node hypotheses and do not represent experimental, pharmacological or clinical confirmation.",
        "",
    ]
    descriptions = {
        "figure_1_top_candidates_meta_priority": "Main ranking view ordered by `meta_priority_score`.",
        "figure_2_priority_vs_confidence": "Shows that `therapeutic_priority_score` and `evidence_confidence_score` are separate outputs.",
        "figure_3_score_decomposition": "Displays score components so the model can be interpreted without treating it as a black box.",
        "figure_4_evolutionary_risk_vs_priority": "Compares evolutionary escape risk with therapeutic priority for review of risk-aware prioritization.",
        "figure_5_ranking_stability": "Summarizes maximum absolute rank movement across sensitivity scenarios.",
        "figure_6_therapeutic_role_distribution": "Counts candidate classifications by therapeutic role.",
    }
    for item in generated:
        lines.extend(
            [
                f"## {item['figure']}",
                "",
                f"- Status: `{item['status']}`",
                f"- Source file: `{item['source_file']}`",
                f"- Interpretation: {descriptions.get(str(item['figure']), 'Interpretative publication figure.')}",
                f"- Manuscript use: descriptive visualization of computational prioritization, not independent confirmation.",
                f"- Note: {item['note']}",
                "",
            ]
        )
        if item["status"] == "generated":
            lines.extend([f"- PNG: `{item['png']}`", f"- SVG: `{item['svg']}`", ""])
    (figures_dir / "publication_figures_interpretation.md").write_text("\n".join(lines), encoding="utf-8")


def _skipped(spec: dict[str, object], reason: str) -> dict[str, object]:
    return {
        "figure": spec["name"],
        "title": spec["title"],
        "source_file": spec["source"],
        "png": None,
        "svg": None,
        "status": "skipped",
        "note": reason,
    }


def _label_column(data: pd.DataFrame) -> str:
    if "gene" in data.columns:
        return "gene"
    if "protein_id" in data.columns:
        return "protein_id"
    return data.columns[0]


def _short_label(value: object, limit: int = 28) -> str:
    text = str(value or "not_reported")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _xml(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
