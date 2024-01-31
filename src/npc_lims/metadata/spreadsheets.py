from __future__ import annotations

import functools
import re
import sqlite3
import tempfile

import openpyxl
import upath

from npc_lims.paths.codeocean import DR_DATA_REPO


def get_training_sqlite_paths() -> tuple[upath.UPath, ...]:
    """
    Examples:
        >>> assert len(get_training_sqlite_paths()) == len(get_training_spreadsheet_paths())
    """
    return tuple(
        path.with_suffix(".sqlite") for path in get_training_spreadsheet_paths()
    )


@functools.cache
def get_training_db(nsb: bool = False) -> sqlite3.Connection:
    """
    Download db to tempdir, open connection, return connection.

    Examples:
        >>> assert get_training_db()
    """
    db_path = upath.UPath(tempfile.mkstemp(suffix=".db")[1])
    s3_path = next(
        path for path in get_training_sqlite_paths() if ("NSB" in path.name) == nsb
    )
    db_path.write_bytes(s3_path.read_bytes())
    con = sqlite3.connect(db_path)

    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    con.row_factory = dict_factory
    return con


def get_training_spreadsheet_paths() -> tuple[upath.UPath, ...]:
    """
    Examples:
        >>> assert len(get_training_spreadsheet_paths()) > 0
    """
    return tuple(DR_DATA_REPO.parent.glob("DynamicRoutingTraining*.xlsx"))


def update_training_dbs() -> None:
    """
    Read spreadsheets from the data repo and write them to corresponding
    databases, currently sqlite files in the same directory.

    Examples:
        >>> update_training_dbs()
    """
    for spreadsheet, sqlite in zip(
        get_training_spreadsheet_paths(), get_training_sqlite_paths()
    ):
        excel_to_sqlite(spreadsheet, sqlite)


def excel_to_sqlite(
    spreadsheet: str | upath.UPath,
    save_path: str | upath.UPath,
) -> upath.UPath:
    """
    This code uses the openpyxl package for playing around with excel using Python code
    to convert complete excel workbook (all sheets) to an SQLite database
    The code assumes that the first row of every sheet is the column name
    Every sheet is stored in a separate table
    The sheet name is assigned as the table name for every sheet.

    From
    https://stackoverflow.com/questions/17439885/export-data-from-excel-to-sqlite-database
    """
    spreadsheet = upath.UPath(spreadsheet)
    save_path = upath.UPath(save_path)

    db_path = tempfile.mkstemp(suffix=".sqlite")[1]
    xls_path = tempfile.mkstemp(suffix=spreadsheet.suffix)[1]
    upath.UPath(xls_path).write_bytes(spreadsheet.read_bytes())

    # Replace with a database name
    con = sqlite3.connect(db_path)

    # replace with the complete path to your excel workbook
    wb = openpyxl.load_workbook(filename=xls_path)

    def slugify(text: str, lower=1) -> str:
        if lower == 1:
            text = text.strip().lower()
        text = text.replace("d'", "dprime")
        text = re.sub(r"[^\w _-]+", "", text)
        text = re.sub(r"[- ]+", "_", text)
        return text

    for sheet in wb.sheetnames:
        ws = wb[sheet]
        columns = []
        duplicate_column_idx = []
        query = (
            "CREATE TABLE "
            + repr(str(slugify(sheet)))
            + "(ID INTEGER PRIMARY KEY AUTOINCREMENT"
        )
        for row in ws.rows:
            for idx, col in enumerate(row):
                column_name = slugify(col.value)
                if column_name not in columns:
                    query += ", " + column_name + " TEXT"
                    columns.append(column_name)
                else:
                    duplicate_column_idx.append(idx)
            break  # only want column names from first row
        query += ");"
        if not columns:
            continue

        con.execute(query)

        tup = []
        for i, col in enumerate(ws):
            tuprow = []
            if i == 0:
                continue
            for idx, col in enumerate(col):
                if idx in duplicate_column_idx:
                    continue
                (
                    tuprow.append(str(col.value).strip())
                    if str(col.value).strip() != "None"
                    else tuprow.append("")
                )
            tup.append(tuple(tuprow))

        insQuery1 = "INSERT INTO " + repr(str(slugify(sheet))) + "("
        insQuery2 = ""
        for col in columns:
            insQuery1 += col + ", "
            insQuery2 += "?, "
        insQuery1 = insQuery1[:-2] + ") VALUES("
        insQuery2 = insQuery2[:-2] + ")"
        insQuery = insQuery1 + insQuery2

        con.executemany(insQuery, tup)
        con.commit()

    con.close()
    save_path.write_bytes(upath.UPath(db_path).read_bytes())
    return save_path


if __name__ == "__main__":
    import doctest

    import dotenv

    dotenv.load_dotenv(dotenv.find_dotenv(usecwd=True))
    doctest.testmod(
        optionflags=(
            doctest.IGNORE_EXCEPTION_DETAIL
            | doctest.NORMALIZE_WHITESPACE
            | doctest.FAIL_FAST
        )
    )
