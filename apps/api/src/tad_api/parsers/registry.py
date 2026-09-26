"""Picks the right parser for an uploaded file.

Adding a new format means adding one parser class and one line here —
nothing calling `get_parser` needs to change.
"""

from tad_api.parsers.base import ParseError, ReportParser
from tad_api.parsers.trf_csv import TrfCsvParser
from tad_api.parsers.trf_json import TrfJsonParser

_PARSERS: list[ReportParser] = [TrfJsonParser(), TrfCsvParser()]


def get_parser(filename: str, content_type: str | None) -> ReportParser:
    for parser in _PARSERS:
        if parser.can_parse(filename, content_type):
            return parser
    raise ParseError(
        f"No parser available for '{filename}' (content-type: {content_type}). "
        "Supported formats: TRF v1 JSON (.json), TRF v1 CSV (.csv)."
    )
