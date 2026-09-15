from app.config import BookConfig
from app.planning.planner import PlannedPage
from app.planning.prompts import generate_prompts, render_prompt


def make_config() -> BookConfig:
    return BookConfig.model_validate(
        {
            "book": {"id": "test_book", "title": "Test Book"},
            "base_elements": ["flower"],
            "compositions": ["organic_all_over"],
            "constraints": ["no text", "no color", "no traditional mandala"],
        }
    )


def make_page(i: int = 1) -> PlannedPage:
    return PlannedPage(
        id=f"TB001-{i:03d}", sequence=i, element="flower", composition="organic_all_over",
        density=4, symmetry="loose", scale="mixed", border="enclosed border", variation_seed=1,
    )


def test_render_prompt_includes_element_and_constraints():
    config = make_config()
    prompt = render_prompt(config, make_page(), family_index=0)
    assert "flower" in prompt
    assert "no text" in prompt
    assert "no traditional mandala" in prompt


def test_different_families_produce_different_wording():
    config = make_config()
    page = make_page()
    variants = {render_prompt(config, page, i) for i in range(6)}
    assert len(variants) > 1, "prompt families should vary wording, not just repeat one template"


def test_generate_prompts_covers_all_pages():
    config = make_config()
    pages = [make_page(1), make_page(2), make_page(3)]
    prompts = generate_prompts(config, pages)
    assert set(prompts.keys()) == {p.id for p in pages}
    assert all(prompts.values())


def test_no_consecutive_duplicate_words_in_any_family():
    """Regression test: a template appending a fixed trailing noun after a
    variable that already ends with that noun (e.g. "...background,
    {{ background }} background") produces an awkward doubled word. This
    happened twice (density_label, then background) before being caught by
    eye - catch it mechanically instead. Covers both providers since they
    assemble the tail of the prompt differently."""
    config = make_config()
    page = make_page()
    for provider in ("midjourney", "generic"):
        for i in range(6):
            prompt = render_prompt(config, page, i, provider=provider)
            words = [w.strip(",.").lower() for w in prompt.split()]
            for a, b in zip(words, words[1:]):
                assert a != b, f"{provider} family {i} repeats the word {a!r} consecutively: {prompt}"


def test_generic_provider_omits_midjourney_flags():
    config = make_config()
    page = make_page()
    prompt = render_prompt(config, page, family_index=0, provider="generic")
    assert "--ar" not in prompt
    assert "--stylize" not in prompt
    assert "--style" not in prompt
    assert "aspect ratio" in prompt


def test_midjourney_provider_includes_flags():
    config = make_config()
    page = make_page()
    prompt = render_prompt(config, page, family_index=0, provider="midjourney")
    assert "--ar" in prompt
    assert "--stylize" in prompt


def test_fixed_style_anchor_overrides_rotation():
    """When style_anchor is set, every family index must use the same
    anchor - the whole point is book-wide cohesion, not per-page variety."""
    config = make_config()
    config.style.style_anchor = "stained glass window"
    page = make_page()
    for i in range(6):
        prompt = render_prompt(config, page, family_index=i)
        assert 'Using a "stained glass window" style' in prompt


def test_no_style_anchor_falls_back_to_rotation():
    """Legacy behavior (books without style_anchor set) still rotates."""
    config = make_config()
    assert config.style.style_anchor is None
    page = make_page()
    anchors_seen = set()
    for i in range(6):
        prompt = render_prompt(config, page, family_index=i)
        anchors_seen.add(prompt.split('Using a "')[1].split('"')[0])
    assert len(anchors_seen) > 1


def test_border_information_never_appears_in_prompts():
    """Border/margin is applied programmatically at PDF-build time
    (app/pdf/build.py), not requested from the image generator - so no
    border phrase, drawn or otherwise, should ever appear in a prompt."""
    config = make_config()
    config.style.border_style = "a solid white border with square corners"
    page = make_page()
    for i in range(6):
        prompt = render_prompt(config, page, family_index=i)
        assert "border" not in prompt.lower()


def test_theme_and_notes_appear_in_prompt():
    config = make_config()
    config.book.theme = "4 Seasons"
    config.style.notes = "extra creative direction"
    page = make_page()
    prompt = render_prompt(config, page, family_index=0)
    assert '"4 Seasons" theme' in prompt
    assert "extra creative direction" in prompt
