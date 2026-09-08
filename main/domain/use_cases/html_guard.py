"""Checking that model-written markup is markup Telegram will accept.

Pure text work, no infrastructure: the same reason ai_guard.py sits here.

Why this exists at all. The generated text is Telegram HTML, because that is
what the channel's own posts look like and what the examples in the template
teach. A model gets markup wrong often enough that it has to be caught, and
catching it at publish time is too late twice over: the post row already
exists, and the admin has already sent the pictures, sent the file and waited
for the generation.
"""
from html import escape
from html.parser import HTMLParser

# Bot API "HTML style", and nothing else. The value is the attributes that tag
# is allowed to carry.
_ALLOWED_TAGS: dict[str, frozenset[str]] = {
    "b": frozenset(),
    "strong": frozenset(),
    "i": frozenset(),
    "em": frozenset(),
    "u": frozenset(),
    "ins": frozenset(),
    "s": frozenset(),
    "strike": frozenset(),
    "del": frozenset(),
    "a": frozenset({"href"}),
    "span": frozenset({"class"}),
    "tg-spoiler": frozenset(),
    "tg-emoji": frozenset({"emoji-id"}),
    "code": frozenset({"class"}),
    "pre": frozenset(),
    "blockquote": frozenset({"expandable"}),
}

# Telegram asks for exactly these three characters to be escaped. Anything else
# a model reaches for - &nbsp; and friends - it may or may not understand, and
# guessing is not worth a broken post.
_ALLOWED_ENTITIES = frozenset({"lt", "gt", "amp", "quot"})

# Handed to the model in the prompt. Lives next to the checker on purpose: a
# hint that drifts from the rule is worse than no hint.
ALLOWED_TAGS_HINT = (
    '<b> <i> <u> <s> <a href="..."> <code> <pre> <blockquote> '
    '<span class="tg-spoiler">'
)


class _Checker(HTMLParser):
    """Collects everything Telegram would refuse, in words a model can act on."""

    def __init__(self) -> None:
        # convert_charrefs=True would quietly turn &nbsp; into a character and
        # hide the very thing being looked for.
        super().__init__(convert_charrefs=False)
        self.problems: list[str] = []
        self.open_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        allowed = _ALLOWED_TAGS.get(tag)

        if allowed is None:
            self.problems.append(f"unknown tag <{tag}>")
            return

        for name, value in attrs:
            if name not in allowed:
                self.problems.append(f"<{tag}> cannot carry the attribute {name!r}")
            elif tag == "span" and value != "tg-spoiler":
                self.problems.append('<span> is only allowed as <span class="tg-spoiler">')

        self.open_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in _ALLOWED_TAGS:
            self.problems.append(f"unknown closing tag </{tag}>")
            return

        if not self.open_tags:
            self.problems.append(f"</{tag}> closes a tag that was never opened")
            return

        if self.open_tags[-1] != tag:
            self.problems.append(
                f"</{tag}> is out of order, <{self.open_tags[-1]}> is still open"
            )

        self.open_tags.pop()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.problems.append(f"<{tag}/> is not a thing here, no tag closes itself")

    def handle_data(self, data: str) -> None:
        # A "<" or "&" that started neither a tag nor an entity arrives here as
        # data - verified against the parser, not assumed. Telegram wants both
        # escaped, so seeing one raw is the error itself.
        if "<" in data:
            self.problems.append("a bare '<' in the text: write it as &lt;")
        if "&" in data:
            self.problems.append("a bare '&' in the text: write it as &amp;")

    def handle_entityref(self, name: str) -> None:
        if name not in _ALLOWED_ENTITIES:
            self.problems.append(f"&{name}; is not an entity Telegram knows")

    def handle_charref(self, name: str) -> None:
        self.problems.append(f"&#{name}; is not supported, write the character itself")

    def handle_comment(self, data: str) -> None:
        self.problems.append("comments are not allowed")

    def handle_decl(self, decl: str) -> None:
        self.problems.append("declarations are not allowed")

    def handle_pi(self, data: str) -> None:
        self.problems.append("processing instructions are not allowed")

    def unknown_decl(self, data: str) -> None:
        self.problems.append("declarations are not allowed")


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return

        for name, value in attrs:
            if name == "href" and value:
                self.hrefs.append(value)


class _Stripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def check_telegram_html(text: str) -> list[str]:
    """Everything Telegram would refuse in this string. Empty list means fine.

    The wording is meant to go straight into a repair prompt: a model fixes a
    named problem far better than it re-rolls a whole post.
    """
    checker = _Checker()
    checker.feed(text)
    checker.close()

    problems = list(checker.problems)
    problems.extend(f"<{tag}> is never closed" for tag in reversed(checker.open_tags))

    # One bare "&" per chunk of text would otherwise repeat the same line a
    # dozen times. Order is kept, which matters: the first problem is usually
    # the one that caused the rest.
    return list(dict.fromkeys(problems))


def strip_tags(text: str) -> str:
    """The visible text with the markup taken out."""
    stripper = _Stripper()
    stripper.feed(text)
    stripper.close()
    return "".join(stripper.parts)


def visible_length(text: str) -> int:
    """Length of the markup-free text, counted the way Telegram counts it.

    Two corrections at once, and both are easy to get wrong. Tags do not count
    towards a caption limit - Telegram measures what a reader sees. And the unit
    is a UTF-16 code unit rather than a character, so an emoji outside the BMP
    takes two.

    Mirrors tg_length in the presentation layer. That one measures what the
    admin typed; this one measures what the model wrote, after its markup is
    gone. Same arithmetic, different subject, and neither layer may import the
    other.
    """
    return len(strip_tags(text).encode("utf-16-le")) // 2


def fallback_plain(text: str) -> str:
    """Markup dropped, words kept, and still safe to publish as HTML.

    Stripping alone is not enough: a "<" that arrived correctly escaped as &lt;
    comes back out of strip_tags as a bare "<", which would break the very post
    this is trying to rescue.
    """
    return escape(strip_tags(text), quote=False)


def extract_links(text: str) -> list[str]:
    """Every address the markup points at, in the order they appear.

    Exists for one check: that a generated post links at its own material and
    at nothing else. The examples the model is shown are previous posts of the
    same channel, each carrying a link to a different file - copying one of
    those produces a post that looks perfect and points at the wrong thing.
    """
    collector = _LinkCollector()
    collector.feed(text)
    collector.close()
    return collector.hrefs
