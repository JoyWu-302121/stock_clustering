"""Create the submission-ready Word report from verified analysis outputs."""

from __future__ import annotations

import csv
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Stock_Clustering_Final_Report.docx"
NAVY = "17365D"
BLUE = "2F5597"
LIGHT_BLUE = "DCE6F1"
LIGHT_GRAY = "F2F4F7"
MID_GRAY = "D9E1F2"
WHITE = "FFFFFF"
TEXT = RGBColor(35, 42, 52)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=70, start=85, bottom=70, end=85) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color="B7C3D0", size="5") -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        node = borders.find(tag)
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), size)
        node.set(qn("w:color"), color)


def repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def keep_row_together(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run("Page ")
    run.font.size = Pt(8)
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr_text, fld_char2])


def add_caption(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph(style="Caption")
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = text.startswith("Table")
    paragraph.add_run(text)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths=None) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    header = table.rows[0]
    repeat_table_header(header)
    for index, value in enumerate(headers):
        cell = header.cells[index]
        cell.text = value
        set_cell_shading(cell, NAVY)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for run in cell.paragraphs[0].runs:
            run.font.bold = True
            run.font.color.rgb = RGBColor(255, 255, 255)
            run.font.size = Pt(8)
        if widths:
            cell.width = Inches(widths[index])
    for row_index, values in enumerate(rows):
        row = table.add_row()
        keep_row_together(row)
        for column_index, value in enumerate(values):
            cell = row.cells[column_index]
            cell.text = str(value)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if row_index % 2:
                set_cell_shading(cell, LIGHT_GRAY)
            if widths:
                cell.width = Inches(widths[column_index])
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.size = Pt(8)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_figure(doc: Document, filename: str, caption: str, width=6.85) -> None:
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    shape = run.add_picture(
        str(ROOT / "outputs" / "figures" / filename), width=Inches(width)
    )
    shape._inline.docPr.set("title", filename)
    shape._inline.docPr.set("descr", caption)
    add_caption(doc, caption)


def add_callout(doc: Document, text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table, color="9FBAD0", size="6")
    cell = table.cell(0, 0)
    set_cell_shading(cell, LIGHT_BLUE)
    set_cell_margins(cell, top=100, start=130, bottom=100, end=130)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(text)
    run.font.bold = True
    run.font.color.rgb = RGBColor(23, 54, 93)
    run.font.size = Pt(9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        paragraph = doc.add_paragraph(style="List Bullet")
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.add_run(item)


def add_code_block(doc: Document, text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table, color="C8CED6", size="4")
    cell = table.cell(0, 0)
    set_cell_shading(cell, "F6F8FA")
    set_cell_margins(cell, top=90, start=110, bottom=90, end=110)
    paragraph = cell.paragraphs[0]
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    run = paragraph.add_run(text.strip())
    run.font.name = "Consolas"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
    run.font.size = Pt(7.2)
    run.font.color.rgb = RGBColor(31, 41, 55)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def setup_styles(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Aptos"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Aptos")
    normal.font.size = Pt(10.2)
    normal.font.color.rgb = TEXT
    normal.paragraph_format.space_after = Pt(5)
    normal.paragraph_format.line_spacing = 1.12

    title = styles["Title"]
    title.font.name = "Aptos Display"
    title.font.size = Pt(27)
    title.font.bold = True
    title.font.color.rgb = RGBColor(23, 54, 93)
    title.paragraph_format.space_after = Pt(12)

    for style_name, size in (("Heading 1", 16), ("Heading 2", 12.5)):
        style = styles[style_name]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(23, 54, 93)
        style.paragraph_format.keep_with_next = True
        style.paragraph_format.space_before = Pt(12)
        style.paragraph_format.space_after = Pt(5)

    caption = styles["Caption"]
    caption.font.name = "Aptos"
    caption.font.size = Pt(8.2)
    caption.font.italic = True
    caption.font.color.rgb = RGBColor(89, 96, 105)
    caption.paragraph_format.space_after = Pt(7)


def configure_section(section) -> None:
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.68)
    section.bottom_margin = Inches(0.82)
    section.left_margin = Inches(0.72)
    section.right_margin = Inches(0.72)
    section.header_distance = Inches(0.3)
    section.footer_distance = Inches(0.30)
    header = section.header.paragraphs[0]
    header.text = "FIM 590-003  |  Project 02"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in header.runs:
        run.font.name = "Aptos"
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(99, 107, 118)
    add_page_number(section.footer.paragraphs[0])


def add_body_paragraph(doc: Document, text: str, bold_lead: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        paragraph.add_run(bold_lead).bold = True
        paragraph.add_run(text[len(bold_lead):])
    else:
        paragraph.add_run(text)


def build_report() -> None:
    clusters = read_rows(ROOT / "data" / "processed" / "cluster_summary.csv")
    favorites = read_rows(ROOT / "data" / "processed" / "favorite_stock_comparison.csv")
    representatives = read_rows(
        ROOT / "data" / "processed" / "representative_stock_comparison.csv"
    )
    prediction = read_rows(ROOT / "data" / "processed" / "new_stock_prediction.csv")[0]
    cv_rows = read_rows(ROOT / "outputs" / "tables" / "knn_cv_results.csv")

    doc = Document()
    doc.core_properties.title = "Stock Classification with K-means and KNN"
    doc.core_properties.author = "Joy Wu; Luolin Zhang; Jialin Zhang"
    doc.core_properties.subject = "FIM 590-003 Project 02"
    setup_styles(doc)
    configure_section(doc.sections[0])

    # Title page
    doc.add_paragraph().paragraph_format.space_after = Pt(62)
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run("Stock Classification\nwith K-means and KNN")
    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_after = Pt(26)
    run = subtitle.add_run("FIM 590-003 Machine Learning in Finance\nProject 02")
    run.font.size = Pt(14)
    run.font.bold = True
    run.font.color.rgb = RGBColor(47, 85, 151)

    line = doc.add_paragraph()
    line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    line.paragraph_format.space_after = Pt(16)
    run = line.add_run("MARKET CAPITALIZATION  •  PEG  •  NINE STYLE CLUSTERS")
    run.font.size = Pt(9)
    run.font.bold = True
    run.font.color.rgb = RGBColor(89, 96, 105)

    for text in ("Joy Wu", "Luolin Zhang", "Jialin Zhang"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(text)
        r.font.size = Pt(12)
    date = doc.add_paragraph()
    date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date.paragraph_format.space_before = Pt(24)
    r = date.add_run("Due November 23, 2026, 11:59 p.m.\nAnalysis completed November 22, 2026")
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(89, 96, 105)
    doc.add_page_break()

    doc.add_heading("Executive summary", level=1)
    add_body_paragraph(
        doc,
        "This project groups the course-provided Russell 2000 sample into nine Size × Style categories using market capitalization and the price/earnings-to-growth (PEG) ratio. The source file contains 1,958 rows. PEG is missing for 797 rows, so the model uses 1,161 observations with complete, positive values. Both features are transformed with log10 and standardized. K-means is then fitted with nine clusters (n_init=50, random_state=42). The silhouette score is 0.3423, which shows moderate separation and overlap between nearby clusters.",
    )
    add_body_paragraph(
        doc,
        "The centroids are first ranked by market capitalization and divided into Small, Mid, and Large groups. Within each group, PEG centroids are ranked from low to high and named Value, Core, and Growth. These labels are defined for this project and do not use Morningstar cutoffs. Of the five documented stocks, two match Morningstar on size. None match on style or the full Style Box. A separate nine-stock check covers one representative from every cluster. Its team-provided source summary reports one exact match, but it does not include the underlying Morningstar links or access dates, so Appendix B presents it as supplementary evidence.",
    )
    add_body_paragraph(
        doc,
        "A distance-weighted KNN classifier is trained to match the K-means labels. Stratified five-fold cross-validation selects k=15. Mean label agreement is 96.90%, with a fold standard deviation of 1.40 percentage points. Bloomberg reports ELF market capitalization at USD 6.120 billion and Estimated PEG at 1.87. Both KNN and a direct K-means check classify ELF as Large Core.",
    )
    add_callout(
        doc,
        "The two models agree on ELF's project label. This agreement does not measure Morningstar accuracy, future returns, or investment quality.",
    )

    doc.add_heading("1. Objective", level=1)
    add_body_paragraph(
        doc,
        "The assignment asks for nine K-means clusters based on market capitalization and PEG. It also asks for economic labels for each cluster, a Morningstar comparison for selected companies, a discussion of the cluster boundaries, and a KNN classification for one new stock. Ticker identifies each company but is not used as a model feature.",
    )

    doc.add_heading("2. Data and audit", level=1)
    add_body_paragraph(
        doc,
        "The supplied data/equity_data.csv has 1,958 unique tickers. Market capitalization has no missing values. PEG is missing for 797 rows (40.70%), so the analysis uses 1,161 rows (59.30%). All retained feature values are positive.",
    )
    add_caption(doc, "Table 1. Source-data audit")
    add_table(
        doc,
        ["Audit item", "Result"],
        [
            ["Source rows / unique tickers", "1,958 / 1,958"],
            ["Missing market capitalization", "0"],
            ["Missing PEG", "797 (40.70%)"],
            ["Rows used", "1,161 (59.30%)"],
            ["Rows excluded", "797"],
        ],
        widths=[4.9, 1.6],
    )
    add_body_paragraph(
        doc,
        "The file does not report the Russell 2000 constituent date, feature observation date, data provider, market-capitalization currency or unit, or PEG definition. We describe it only as the course-provided Russell 2000 sample. We do not infer the missing source details.",
    )

    doc.add_heading("3. Preprocessing and model design", level=1)
    add_body_paragraph(
        doc,
        "The two raw features are right-skewed, and their scales differ. Rows with a missing or nonpositive value are removed. The remaining values are transformed with log10 and standardized. K-means and the direct K-means check use a scaler fitted to the training sample. During KNN cross-validation, the scaler is fitted again within each training fold. This keeps information from the held-out fold out of preprocessing.",
    )
    add_body_paragraph(
        doc,
        "The assignment requires nine clusters to represent the nine Size × Style combinations. The number of clusters is fixed rather than selected from the silhouette score. The centroids are ordered by back-transformed market capitalization and split into three groups of three called Small, Mid, and Large. Within each group, the PEG centroids are ordered from low to high and called Value, Core, and Growth.",
    )
    add_body_paragraph(
        doc,
        "Because the model is fitted on logged features, the back-transformed centroids act like geometric centers. They are not arithmetic means or fixed financial cutoffs.",
    )

    doc.add_heading("4. K-means results", level=1)
    cluster_rows = []
    for row in clusters:
        cluster_rows.append(
            [
                row["Style_Label"],
                row["Raw_Cluster"],
                f"{float(row['Center_Market_capital_billions']):.3f}",
                f"{float(row['Center_PEG_ratio']):.3f}",
                f"{int(float(row['Stock_Count'])):,}",
                f"{float(row['Stock_Share']):.1%}",
            ]
        )
    add_caption(doc, "Table 2. Nine K-means clusters and back-transformed log-space centroids")
    add_table(
        doc,
        ["Project label", "Raw", "Mkt cap\n(source ÷ 1B)", "PEG", "Stocks", "Share"],
        cluster_rows,
        widths=[1.75, 0.52, 1.16, 0.85, 0.72, 0.72],
    )
    add_figure(
        doc,
        "kmeans_clusters.png",
        "Figure 1. K-means clusters and decision regions for the complete-case sample (n=1,161). Black X marks are centroids.",
        width=6.75,
    )
    add_body_paragraph(
        doc,
        "K-means assigns each stock to its nearest centroid. The boundaries are straight lines in standardized log-feature space and appear as sloped regions on the log-scale plot. Morningstar uses a rectangular Style Box and more than two factors, so the plotted regions should not be read as Morningstar cutoffs. The silhouette score of 0.3423 shows moderate separation and overlap between nearby clusters.",
    )
    add_figure(
        doc,
        "cluster_sizes.png",
        "Figure 2. Membership counts across the nine project clusters.",
        width=6.55,
    )
    add_body_paragraph(
        doc,
        "Large Core contains the most stocks, with 221 observations or 19.0% of the sample. Small Value contains the fewest, with 43 observations or 3.7%. K-means minimizes within-cluster squared distance and does not require clusters to have equal sizes.",
    )

    doc.add_heading("5. Morningstar comparison", level=1)
    add_body_paragraph(
        doc,
        "The Morningstar pages were accessed on November 22, 2026. None of the reviewed pages displayed a separate effective date for the Stock Style Box, so the date field is recorded as Not shown.",
    )
    favorite_rows = []
    for row in favorites:
        favorite_rows.append(
            [
                row["Ticker"],
                row["KMeans_Style_Label"],
                row["Morningstar_Style_Label"],
                "Yes" if row["Size_Match"] == "True" else "No",
                "Yes" if row["Style_Match"] == "True" else "No",
            ]
        )
    add_caption(doc, "Table 3. Five selected Morningstar comparison cases")
    add_table(
        doc,
        ["Ticker", "Model", "Morningstar", "Size", "Style"],
        favorite_rows,
        widths=[0.75, 1.62, 1.62, 0.72, 0.72],
    )
    add_body_paragraph(
        doc,
        "KODK and PZZA match Morningstar on size but not on style. ROOT, HOG, and RRR match on neither dimension. None of the five stocks matches the full Morningstar Style Box. The project model uses only market capitalization and PEG, while Morningstar uses additional factors. The five stocks were chosen for discussion rather than as a random validation sample. The 0/5 result does not estimate performance for all stocks.",
    )
    add_figure(
        doc,
        "selected_stocks.png",
        "Figure 3. Locations of the five Morningstar cases and ELF relative to the training sample.",
        width=6.65,
    )
    add_body_paragraph(
        doc,
        "Appendix B adds a separate check using the stock closest to each of the nine fitted centroids. It is not combined with the five documented cases because the uploaded summary does not include the original Morningstar links or access dates.",
    )

    doc.add_heading("6. KNN model selection", level=1)
    add_body_paragraph(
        doc,
        "KNN uses the same two log-transformed features. Its target is the set of nine labels produced by K-means. Several values of k are tested with shuffled, stratified five-fold cross-validation and distance weighting.",
    )
    formatted_cv = []
    for row in cv_rows:
        formatted_cv.append(
            [
                row["k"],
                f"{float(row['Mean_CV_Accuracy']):.2%}",
                f"{100 * float(row['SD_CV_Accuracy']):.2f} pp",
            ]
        )
    add_caption(doc, "Table 4. KNN cross-validation agreement with K-means-derived labels")
    add_table(
        doc,
        ["Neighbors (k)", "Mean agreement", "Fold SD"],
        formatted_cv,
        widths=[1.45, 2.15, 1.6],
    )
    add_figure(
        doc,
        "knn_cross_validation.png",
        "Figure 4. Five-fold mean KNN agreement; error bars show one fold standard deviation.",
        width=6.25,
    )
    add_body_paragraph(
        doc,
        "The candidate scores are close, and their fold variation overlaps. k=15 has the highest mean score, but it is only about 0.17 percentage point above k=21. The reported 96.90% is agreement with K-means labels created from the same two features. It does not measure agreement with Morningstar, future investment returns, or an independent classification standard.",
    )

    doc.add_heading("7. ELF classification", level=1)
    add_body_paragraph(
        doc,
        "ELF (e.l.f. Beauty, Inc.) does not appear in the training file. Bloomberg Terminal (ELF US Equity > DES > Profile) displayed Mkt Cap (USD) 6,120.0M and Est PEG 1.87 when accessed on November 22, 2026. The model inputs are 6,120,000,000 and 1.87. The separate BEST_PEG_RATIO field returned N.A. and is not used.",
    )
    elf_rows = [
        ["Market capitalization", "USD 6.120 billion"],
        ["PEG", "1.87, Bloomberg Estimated PEG"],
        ["Market-cap percentile", f"{float(prediction['Market_capital_percentile']):.1%}"],
        ["PEG percentile", f"{float(prediction['PEG_ratio_percentile']):.1%}"],
        ["KNN prediction", prediction["KNN_Style_Label"]],
        ["Direct K-means check", prediction["KMeans_Style_Label"]],
        ["Model agreement", "Yes" if prediction["Prediction_Agreement"] == "True" else "No"],
    ]
    add_caption(doc, "Table 5. ELF inputs and model result")
    add_table(doc, ["Item", "Result"], elf_rows, widths=[2.4, 4.0])
    add_callout(
        doc,
        "Both models classify ELF as Large Core. This is an internal check, not a Morningstar Style Box result.",
    )
    add_body_paragraph(
        doc,
        "Each ELF input falls within the observed range for that feature in the training sample. ELF is not outside the training range on either feature. KNN and K-means return the same label, but this is only an internal consistency check. The training file does not state its market-capitalization currency or unit, or its PEG definition. The ELF classification assumes that the training market-cap values use a scale comparable to the Bloomberg USD value. It also uses Estimated PEG even though the training PEG convention is unknown.",
    )

    doc.add_heading("8. Discussion and limitations", level=1)
    add_bullets(
        doc,
        [
            "Data coverage and source details: PEG is missing for 40.70% of the source rows. The complete-case sample may differ from the excluded stocks. The training file also omits the constituent date, observation date, provider, and feature definitions. Index membership and company values can change over time.",
            "Feature comparability: Bloomberg reports ELF's value as Estimated PEG, while the training PEG definition is unknown. The training market-capitalization currency and unit are also undocumented.",
            "Model scope: The model uses only market capitalization and PEG, so it cannot reproduce Morningstar's multi-factor method. The Size × Style names are based on the order of the fitted centroids, not external cutoff points. The silhouette score of 0.3423 also shows that nearby clusters overlap.",
            "Validation scope: KNN cross-validation measures agreement with K-means labels, not with an independent target. The five documented Morningstar stocks are selected examples and cannot support an accuracy claim for the full stock sample. The separate nine-stock summary lacks the original Morningstar links and access dates, so it is reported only as supplementary evidence.",
        ],
    )

    doc.add_heading("9. Conclusion", level=1)
    add_body_paragraph(
        doc,
        "After log transformation and standardization, K-means divides the 1,161 complete observations into the nine required Size × Style categories. These labels are relative to this sample and are not Morningstar definitions. The five selected stocks show that the model can agree with Morningstar on size while disagreeing on style. With k=15, KNN matches the K-means labels in 96.90% of cross-validation predictions and classifies ELF as Large Core. K-means gives the same ELF label. This result shows consistency between the two project models. It does not measure Morningstar accuracy or investment performance.",
    )

    doc.add_page_break()
    doc.add_heading("Appendix A. Key Python code", level=1)
    add_body_paragraph(
        doc,
        "The report includes the main code used for the analysis. The full code is in src/stock_clustering.py, and model/model.ipynb contains the executed results.",
    )
    doc.add_heading("A.1 Cleaning, transformation, and scaling", level=2)
    add_code_block(
        doc,
        '''valid = df[["Market_capital", "PEG ratio"]].notna().all(axis=1)
valid &= (df[["Market_capital", "PEG ratio"]] > 0).all(axis=1)
modeled = df.loc[valid].copy()
modeled["Log10_Market_capital"] = np.log10(modeled["Market_capital"])
modeled["Log10_PEG_ratio"] = np.log10(modeled["PEG ratio"])

scaler = StandardScaler()
scaled = scaler.fit_transform(
    modeled[["Log10_Market_capital", "Log10_PEG_ratio"]]
)''',
    )
    doc.add_heading("A.2 K-means and project-label rule", level=2)
    add_code_block(
        doc,
        '''kmeans = KMeans(n_clusters=9, n_init=50, random_state=42)
raw_labels = kmeans.fit_predict(scaled)

# Sort centroids by market cap, then PEG within each size group.
market_order = centers.sort_values("Center_Market_capital").index.to_list()
for size_index, size_name in enumerate(["Small", "Mid", "Large"]):
    group = market_order[size_index * 3:(size_index + 1) * 3]
    peg_order = centers.loc[group].sort_values("Center_PEG_ratio").index
    for growth_name, raw_cluster in zip(
        ["Value", "Core", "Growth"], peg_order
    ):
        style_label = f"{size_name} {growth_name}"''',
    )
    doc.add_heading("A.3 KNN cross-validation and ELF prediction", level=2)
    add_code_block(
        doc,
        '''pipeline = Pipeline([
    ("scaler", StandardScaler()),
    ("knn", KNeighborsClassifier(n_neighbors=k, weights="distance")),
])
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(pipeline, X_log, kmeans_style_labels,
                         cv=cv, scoring="accuracy")

knn.fit(X_log, kmeans_style_labels)
elf_log = [[np.log10(6_120_000_000), np.log10(1.87)]]
elf_label = knn.predict(elf_log)  # Large Core''',
    )

    doc.add_page_break()
    doc.add_heading("Appendix B. Supplementary cluster representatives", level=1)
    add_body_paragraph(
        doc,
        "For each cluster, the representative stock is the observation closest to the fitted centroid in standardized log-feature space. The model reproduces the nine representatives shown in the team comparison. The summary reports three size matches, three style matches, and one exact match. Because it does not include the original Morningstar links, access dates, or individual source screenshots, these results are not combined with the five documented cases.",
    )
    representative_rows = []
    for row in representatives:
        representative_rows.append(
            [
                row["Ticker"],
                row["Model_Label"],
                row["Morningstar_Label"],
                row["Difference"],
            ]
        )
    add_caption(doc, "Table B1. Nine cluster representatives and team-provided comparison")
    add_table(
        doc,
        ["Ticker", "Model", "Team summary", "Difference"],
        representative_rows,
        widths=[0.8, 1.8, 1.8, 1.15],
    )
    add_body_paragraph(
        doc,
        "Evidence record: K-Means Comparison.png, GitHub commit 4fd2bfc77d111f510a3db60e104698e75a8f2e61. The commit date is not treated as the Morningstar access date.",
    )

    doc.add_heading("References and data sources", level=1)
    references = [
        "1. FIM 590-003, Project 02 assignment (Project_Overview.pdf).",
        "2. Course-provided stock file (data/equity_data.csv); source metadata not supplied.",
        "3. Morningstar stock pages for KODK, PZZA, ROOT, HOG, and RRR, accessed November 22, 2026; direct URLs are stored in data/input/favorite_stocks.csv.",
        "4. Bloomberg Terminal, ELF US Equity > DES > Profile, accessed November 22, 2026.",
        "5. Team-provided K-Means Comparison.png, GitHub commit 4fd2bfc77d111f510a3db60e104698e75a8f2e61, November 22, 2026; original Morningstar access dates were not supplied.",
    ]
    for reference in references:
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.18)
        paragraph.paragraph_format.first_line_indent = Inches(-0.18)
        paragraph.add_run(reference)

    doc.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build_report()
