from typing import Optional

from parsing.parser import Parser

_parser: Optional[Parser] = None
_parser_error: Optional[Exception] = None


def get_parser() -> Parser:
    global _parser, _parser_error
    if _parser is not None:
        return _parser
    if _parser_error is not None:
        raise _parser_error
    try:
        _parser = Parser()
        return _parser
    except Exception as exc:
        _parser_error = exc
        raise


def parse_text(text: str):
    return get_parser().parse(text)


def get_nlp_status() -> str:
    if _parser is not None:
        return "ready"
    if _parser_error is not None:
        return "missing_model"
    return "not_loaded"

