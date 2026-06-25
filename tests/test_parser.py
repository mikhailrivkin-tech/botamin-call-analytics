from src.parser import parse_duration_to_seconds


def test_parse_duration_to_seconds_short_call():
    assert parse_duration_to_seconds("0:03") == 3


def test_parse_duration_to_seconds_one_minute():
    assert parse_duration_to_seconds("1:27") == 87