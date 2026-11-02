# KavoshELT MCP server

`kavosh-mcp` exposes the curriculum database over the
[Model Context Protocol](https://modelcontextprotocol.io) (stdio transport) so
agents such as Claude Desktop, Cursor or Hermes can validate and author
content that stays inside the Iranian national ELT syllabus.

## Install

```bash
pip install -e ".[dev]"      # from a checkout
# or: pip install kavosh-elt  (wheel ships a prebuilt curriculum database)
kavosh-mcp --version
```

Supports both MCP Python SDK majors (`mcp>=1.2`, including 2.x).

## Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `validate_text` | `text`, `target_grade` (7-12), `target_lesson?` | `{is_valid, out_of_bounds_tokens, violations}` |
| `suggest_synonyms` | `text`, `target_grade` | per out-of-bounds word, ranked in-syllabus replacements |
| `get_lesson_bounds` | `grade`, `lesson` | vocabulary, grammar formulas, functions, forbidden structures |
| `search_curriculum` | `query`, `grade?`, `limit=5` | hybrid semantic + FTS5 hits over readings and conversations |
| `retrieve_exam_questions` | `section?`, `topic?`, `limit=5` | authentic national-exam items (grade 12) with keys, rubrics, distractor notes |
| `get_l1_interference` | `category?` | Persian-to-English negative-transfer patterns |

Invalid input (e.g. grade outside 7-12) is reported as an MCP tool error.

## Resources

- `curriculum://grade/{grade}/lesson/{lesson}` - conversation, reading, vocabulary and grammar of one lesson (markdown)
- `curriculum://index` - list of all lesson resources

## Configuration

| Variable | Purpose |
| --- | --- |
| `KAVOSH_DB` | Path to a prebuilt SQLite database (or use `--db`) |
| `KAVOSH_CACHE_DIR` | Where a database is built if none is packaged |
| `KAVOSH_EXPORTS_DIR` | Output directory for composed exams |

Resolution order: `--db` / `KAVOSH_DB` -> database packaged in the wheel ->
cached build keyed by a fingerprint of the dataset files (rebuilt automatically
when datasets change).

## Client setup

Claude Desktop (`claude_desktop_config.json`), see `examples/`:

```json
{ "mcpServers": { "kavosh-elt": { "command": "kavosh-mcp" } } }
```

If the console script is not on the client's `PATH`, use the absolute path to
your venv's Python with `args: ["-m", "kavosh.mcp_server"]`
(`examples/claude_desktop_config.advanced.json`). Cursor and other stdio MCP
clients take the same `command` / `args` / `env` fields.

## Data integrity

`kavosh integrity [--strict]` audits the curriculum dataset (schema, duplicate
IDs, answer keys, concept edges, missing distractor analyses, lessons without
listening scripts). `tests/test_curriculum_integrity.py` fails on any *error*;
warnings are reported but not fatal.
