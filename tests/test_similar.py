from recommendations.similar import Neighbour, choose


def pool(size: int) -> list[Neighbour]:
    """A ranked pool, best first, as the query returns it."""
    return [Neighbour(movie_id=f"film-{i}", score=1 - i / 100) for i in range(size)]


def test_without_shuffle_the_best_come_back_in_rank_order():
    """An evaluation cannot measure a list that changes between runs."""
    assert [n.movie_id for n in choose(pool(20), limit=5, shuffle=False)] == [
        "film-0",
        "film-1",
        "film-2",
        "film-3",
        "film-4",
    ]


def test_shuffling_returns_the_right_number():
    assert len(choose(pool(20), limit=12, shuffle=True)) == 12


def test_shuffling_never_repeats_a_film():
    chosen = choose(pool(20), limit=12, shuffle=True)

    assert len({n.movie_id for n in chosen}) == 12


def test_shuffling_only_ever_draws_from_the_pool():
    """Variety costs relevance down to the pool's worst member, and no further."""
    allowed = {n.movie_id for n in pool(20)}

    for _ in range(50):
        assert {n.movie_id for n in choose(pool(20), limit=12, shuffle=True)} <= allowed


def test_two_rows_from_the_same_film_differ():
    """The whole reason shuffling exists: the same film's neighbours appear in more than one
    place on a page, and two identical rows read as a bug."""
    runs = {tuple(n.movie_id for n in choose(pool(20), limit=12, shuffle=True)) for _ in range(20)}

    assert len(runs) > 1


def test_a_pool_smaller_than_the_limit_returns_what_there_is():
    """A film with few neighbours must not raise, and must not pad."""
    assert len(choose(pool(3), limit=12, shuffle=True)) == 3
    assert len(choose(pool(3), limit=12, shuffle=False)) == 3


def test_no_candidates_returns_nothing():
    assert choose([], limit=12, shuffle=True) == []
