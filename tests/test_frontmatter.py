import unittest

from ivo_skills.frontmatter import FrontmatterError, parse_frontmatter


class ParseFrontmatterTest(unittest.TestCase):
    def test_simple_fields(self):
        text = "---\nname: grill-me\ndescription: A relentless interview.\n---\nBody"
        self.assertEqual(parse_frontmatter(text),
                         {"name": "grill-me", "description": "A relentless interview."})

    def test_value_containing_colon(self):
        text = "---\ndescription: Use when: planning\n---\n"
        self.assertEqual(parse_frontmatter(text)["description"], "Use when: planning")

    def test_quoted_value(self):
        text = '---\nname: "grilling"\n---\n'
        self.assertEqual(parse_frontmatter(text)["name"], "grilling")

    def test_folded_block_description(self):
        text = "---\nname: x\ndescription: >\n  First line\n  second line.\n---\n"
        self.assertEqual(parse_frontmatter(text)["description"], "First line second line.")

    def test_nested_values_are_ignored(self):
        text = "---\nname: x\nmetadata:\n  owner: someone\n---\n"
        self.assertEqual(parse_frontmatter(text), {"name": "x", "metadata": ""})

    def test_missing_opening_line(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("name: x\n")

    def test_unclosed(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("---\nname: x\n")

    def test_line_without_colon(self):
        with self.assertRaises(FrontmatterError):
            parse_frontmatter("---\njust words\n---\n")
