from hashlib import sha256

from recs.catalogue import Movie

# Cast is a real similarity signal, but a long list of names drowns out the plot. Five is a
# guess worth revisiting: the document hash makes trying another number cost one rebuild.
CAST_NAMES = 5


def build_document(movie: Movie) -> str:
    """The text that gets embedded.

    This is the highest-leverage choice in the pipeline. The model only ever sees this string,
    so anything left out of it cannot influence which films come back as similar.
    """
    lines = [f"{movie.title} ({movie.release_year})"]

    if movie.genres:
        lines.append("Genres: " + ", ".join(movie.genres))

    if movie.cast:
        lines.append("Starring: " + ", ".join(movie.cast[:CAST_NAMES]))

    lines.append(movie.overview)

    return "\n".join(lines)


def document_hash(document: str) -> str:
    """A fingerprint of the exact text embedded, so a rebuild can skip what has not changed."""
    return sha256(document.encode("utf-8")).hexdigest()
