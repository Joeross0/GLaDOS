from glados.core.style_model import build_card, extract_lines, retrieve_lines


SAMPLE = '''
Introduction
"Hello and, again, welcome to the Aperture Science computer-aided enrichment center." | Download
"Please be careful." | Play
If the player dies
"The floor here will kill you - try to avoid it." | Download
'''


def test_extract_skips_wiki_chrome() -> None:
    lines = extract_lines(SAMPLE)
    assert any("enrichment center" in line.lower() for line in lines)
    assert any("kill you" in line.lower() for line in lines)
    assert any("please be careful" in line.lower() for line in lines)
    assert all("Download" not in line for line in lines)


def test_extract_keeps_test_chamber_lines() -> None:
    lines = extract_lines('"Welcome to test chamber four." | Download Download |  Play\n')
    assert any("test chamber four" in line.lower() for line in lines)


def test_retrieve_prefers_overlap() -> None:
    lines = extract_lines(SAMPLE)
    picks = retrieve_lines("the floor is dangerous", lines, limit=2)
    assert picks
    assert "kill you" in picks[0].lower()


def test_card_mentions_count() -> None:
    lines = extract_lines(SAMPLE)
    card = build_card(lines)
    assert "TRAINED VOICE" in card
    assert str(len(lines)) in card
