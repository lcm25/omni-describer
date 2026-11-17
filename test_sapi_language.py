"""SAPI Language values like '409;9' must not discard the voice list."""
import sapi32
from audio_describer.core.sapi_voices import collect_voice_records, parse_sapi_language


def test_parser(parse):
    assert parse("409;9") == [0x409, 0x9]
    assert parse("416") == [0x416]
    assert parse("") == []
    assert parse(None) == []
    assert parse("not-a-language") == []
    assert parse("409;nope;416") == [0x409, 0x416]


def test_one_bad_token_keeps_the_rest():
    voices = collect_voice_records([
        {"description": "Microsoft Maria", "id": "maria", "language": "416"},
        {"description": "Broken", "id": "broken", "language": "409;9"},
        {"description": "Garbage", "id": "garbage", "language": "nope"},
        {"description": "", "id": "", "language": "409"},
        {"description": "Microsoft Daniel", "id": "daniel", "language": ""},
    ])
    assert [item["id"] for item in voices] == ["maria", "broken", "garbage", "daniel"]


if __name__ == "__main__":
    test_parser(parse_sapi_language)
    test_parser(sapi32.parse_sapi_language)
    test_one_bad_token_keeps_the_rest()
    print("sapi language checks passed")
