"""Read the simple YAML front matter used in SKILL.md files, without PyYAML."""

BLOCK_MARKERS = (">", "|", ">-", "|-")


class FrontmatterError(ValueError):
    pass


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("file must start with a '---' front matter line")
    fields: dict[str, str] = {}
    block_key = None
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        if line[:1] in (" ", "\t"):
            # Continuation of a block value, or part of a nested value we do not need.
            if block_key:
                fields[block_key] = (fields[block_key] + " " + line.strip()).strip()
            continue
        block_key = None
        if not line.strip() or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not sep or not key:
            raise FrontmatterError(f"expected 'key: value', got {line!r}")
        if value in BLOCK_MARKERS:
            fields[key] = ""
            block_key = key
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
    raise FrontmatterError("front matter is not closed with '---'")
