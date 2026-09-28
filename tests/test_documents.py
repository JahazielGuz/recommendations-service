from recommendations.catalogue import Movie
from recommendations.documents import CAST_NAMES, build_document, document_hash


def movie(**overrides) -> Movie:
    """A film with every field populated, so each test changes exactly one thing."""
    fields = {
        "id": "01a0add2-fac4-703a-b659-ca2176d1148f",
        "title": "Spider-Man: Brand New Day",
        "release_year": 2026,
        "genres": ["Action", "Adventure"],
        "cast": ["Tom Holland", "Zendaya"],
        "overview": "Fighting crime full-time in a world that doesn't remember him.",
    }
    return Movie(**{**fields, **overrides})


def test_document_has_a_line_per_part():
    assert build_document(movie()).split("\n") == [
        "Spider-Man: Brand New Day (2026)",
        "Genres: Action, Adventure",
        "Starring: Tom Holland, Zendaya",
        "Fighting crime full-time in a world that doesn't remember him.",
    ]


def test_missing_genres_leaves_no_empty_line():
    """A blank "Genres:" would be embedded as if it meant something."""
    assert "Genres" not in build_document(movie(genres=[]))


def test_missing_cast_leaves_no_empty_line():
    assert "Starring" not in build_document(movie(cast=[]))


def test_billing_is_capped():
    """Cast is a similarity signal, but an uncapped list drowns out the plot."""
    names = [f"Actor {index}" for index in range(20)]
    starring = build_document(movie(cast=names)).split("\n")[2]

    assert starring.count(",") == CAST_NAMES - 1
    assert "Actor 0" in starring and f"Actor {CAST_NAMES}" not in starring


def test_the_overview_is_included_in_full():
    """The plot is the largest signal; truncating it silently would be invisible."""
    assert movie().overview in build_document(movie())


def test_hash_is_stable_for_the_same_text():
    assert document_hash(build_document(movie())) == document_hash(build_document(movie()))


def test_hash_changes_when_any_part_changes():
    """This is what decides whether a film is re-embedded, so it has to notice everything."""
    base = document_hash(build_document(movie()))

    for changed in [
        movie(title="Something Else"),
        movie(release_year=1999),
        movie(genres=["Horror"]),
        movie(cast=["Someone Else"]),
        movie(overview="A different plot."),
    ]:
        assert document_hash(build_document(changed)) != base
