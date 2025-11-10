import os
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


@dataclass
class ColumnStatus:
    name: str
    is_complete: bool
    complete_count: int
    missing_count: int
    completion_rate: float
    dtype: str


@dataclass
class WordResult:
    name: str
    count: int
    percentage: float


@dataclass
class WordExample:
    name: str
    row_number: int
    value: str


@dataclass
class MissingBreakdown:
    name: str
    missing_count: int
    percentage: float


@dataclass
class DatasetStats:
    num_rows: int
    num_columns: int
    num_duplicates: int
    total_missing: int
    missing_percentage: float
    complete_columns_count: int
    complete_columns: List[str]
    all_columns: List[ColumnStatus]
    filtered_columns: List[ColumnStatus]
    column_names: List[str]
    dtypes: Dict[str, str]
    missing_breakdown: List[MissingBreakdown]
    word_results: List[WordResult]
    word_examples: List[WordExample]
    word_total_occurrences: int


def create_app() -> Flask:
    app = Flask(__name__)
    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not secret_key:
        secret_key = os.urandom(24)
    app.secret_key = secret_key

    app.config.setdefault("MAX_CONTENT_LENGTH", 50 * 1024 * 1024)  # 50 MB

    return app


app = create_app()

# تخزين البيانات لكل جلسة
DATASETS: Dict[str, pd.DataFrame] = {}

# الحقول المستثناة من حساب الأعمدة المكتملة
EXCLUDED_COLUMNS = [
    "CreatedAt",
    "ModifiedAt",
    "DeletedAt",
    "IsDeleted",
    "CreatedById",
    "ModifiedById",
    "DeletedById",
    "Governorate",
]


def _get_dataset() -> Optional[pd.DataFrame]:
    upload_id = session.get("upload_id")
    if not upload_id:
        return None
    return DATASETS.get(upload_id)


def _set_dataset(df: pd.DataFrame) -> None:
    upload_id = str(uuid.uuid4())
    # تنظيف التخزين في حال وجود معرف سابق
    old_id = session.pop("upload_id", None)
    if old_id and old_id in DATASETS:
        DATASETS.pop(old_id, None)
    DATASETS[upload_id] = df
    session["upload_id"] = upload_id


def _clear_dataset() -> None:
    upload_id = session.pop("upload_id", None)
    if upload_id:
        DATASETS.pop(upload_id, None)


def analyze_dataframe(
    df: pd.DataFrame, column_query: str = "", word_query: str = ""
) -> DatasetStats:
    num_rows, num_columns = df.shape
    num_duplicates = int(df.duplicated().sum())

    missing_data = df.isnull().sum()
    total_missing = int(missing_data.sum())
    total_cells = num_rows * num_columns
    missing_percentage = (total_missing / total_cells * 100) if total_cells else 0.0

    columns_to_check = [col for col in df.columns if col not in EXCLUDED_COLUMNS]
    complete_columns = [col for col in columns_to_check if df[col].notna().all()]
    complete_columns_count = len(complete_columns)

    all_columns: List[ColumnStatus] = []
    for col in columns_to_check:
        series = df[col]
        missing_count = int(series.isnull().sum())
        complete_count = int(series.notna().sum())
        completion_rate = (complete_count / num_rows * 100) if num_rows else 0.0

        all_columns.append(
            ColumnStatus(
                name=col,
                is_complete=missing_count == 0,
                complete_count=complete_count,
                missing_count=missing_count,
                completion_rate=completion_rate,
                dtype=str(series.dtype),
            )
        )

    filtered_columns = (
        [
            status
            for status in all_columns
            if column_query.lower() in status.name.lower()
        ]
        if column_query
        else []
    )

    missing_breakdown = [
        MissingBreakdown(
            name=col,
            missing_count=int(count),
            percentage=((count / num_rows) * 100) if num_rows else 0.0,
        )
        for col, count in missing_data.items()
        if count > 0
    ]
    missing_breakdown.sort(key=lambda item: item.missing_count, reverse=True)

    word_results: List[WordResult] = []
    word_examples: List[WordExample] = []
    word_total_occurrences = 0

    if word_query:
        lowered_word = word_query.lower()
        for col in columns_to_check:
            series_text = df[col].astype(str)
            matches = series_text.str.contains(
                lowered_word, case=False, na=False, regex=False
            )
            count = int(matches.sum())
            if count > 0:
                percentage = (count / num_rows * 100) if num_rows else 0.0
                word_total_occurrences += count
                word_results.append(
                    WordResult(name=col, count=count, percentage=percentage)
                )

                matched_indices = df.loc[matches].index[:3].tolist()
                for idx in matched_indices:
                    value = str(df.loc[idx, col])
                    word_examples.append(
                        WordExample(name=col, row_number=int(idx) + 1, value=value)
                    )

        word_results.sort(key=lambda result: result.count, reverse=True)
        word_examples = word_examples[:10]

    return DatasetStats(
        num_rows=num_rows,
        num_columns=num_columns,
        num_duplicates=num_duplicates,
        total_missing=total_missing,
        missing_percentage=missing_percentage,
        complete_columns_count=complete_columns_count,
        complete_columns=complete_columns,
        all_columns=all_columns,
        filtered_columns=filtered_columns,
        column_names=df.columns.tolist(),
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
        missing_breakdown=missing_breakdown,
        word_results=word_results,
        word_examples=word_examples,
        word_total_occurrences=word_total_occurrences,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("يرجى اختيار ملف CSV صالح.", "warning")
            return redirect(url_for("index"))

        if not file.filename.lower().endswith(".csv"):
            flash("يُسمح فقط بملفات CSV.", "danger")
            return redirect(url_for("index"))

        try:
            df = pd.read_csv(file)
        except Exception as exc:  # pylint: disable=broad-except
            flash(f"تعذّر قراءة الملف: {exc}", "danger")
            return redirect(url_for("index"))

        if df.empty:
            flash("الملف لا يحتوي على بيانات.", "warning")
            return redirect(url_for("index"))

        _set_dataset(df)
        flash("تم رفع الملف وتحليله بنجاح.", "success")
        return redirect(url_for("index"))

    df = _get_dataset()
    stats = None
    preview_html = None

    column_query = request.args.get("column_search", "").strip()
    word_query = request.args.get("word_search", "").strip()

    if df is not None:
        stats = analyze_dataframe(df, column_query=column_query, word_query=word_query)
        preview_html = df.head(10).to_html(
            classes="table table-striped table-bordered table-sm", justify="center"
        )

    return render_template(
        "index.html",
        stats=stats,
        preview_html=preview_html,
        column_query=column_query,
        word_query=word_query,
        excluded_columns=EXCLUDED_COLUMNS,
    )


@app.route("/reset")
def reset():
    _clear_dataset()
    flash("تم حذف الملف الحالي.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 8501)))

