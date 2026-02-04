---
name: simpledoc
description: Create or update documentation in this repo following SimpleDoc conventions.
---

# SimpleDoc Documentation Skill

Use this skill whenever you are asked to create or update documentation in this repository.

## MUST DO SETUP

**Attention agent!** This section is a template for creating instructions on how to create documentation in this repository. The placeholder sections must be filled in before anything else.

1. Fetch the most recent SimpleDoc specification from https://github.com/osolmaz/SimpleDoc and copy it below, replacing the placeholder content.
2. Ask the user about their preferences in documentation style (tone, technicality, planning style, etc.). Do a few rounds of back-and-forth to get the user's preferences, then replace the placeholder content in the Preferences section.

After finishing the setup, DELETE ONLY this section between dividers `---`. The other agent instruction below is to be kept as is.

---

**Attention agent!** Complete every item below before touching documentation work:

1. **Read this file in full for the current session.** No shortcuts.
2. **Verify that git is initialized and configured.** You will need the name and email of the current user in order to populate the `author` field in the YAML frontmatter. Run the following one-liner to verify:

```bash
printf '%s <%s>\n' "$(git config --local --get user.name 2>/dev/null || git config --global --get user.name)" "$(git config --local --get user.email 2>/dev/null || git config --global --get user.email)"
```

If the name and email are not available for some reason, ask the user to provide them, and also setup git configuration for them.

## SimpleDoc Specification

```
<Replace this part with the content of SimpleDoc specification>
```

## Preferences in Documentation Style

```
<Replace this part with the user's preferences in documentation style>
```

## Before You Start

1. Run `date +%Y-%m-%d` and use the output for both filename prefix and `date` field.
2. Identify where the document belongs:
   - Keep general documentation at the root of `docs/`.
   - If exists, use the dedicated subdirectories for specialized content.
3. Check for existing, related docs to avoid duplicates and to link to prior work.

## File Naming

- Format: `YYYY-MM-DD-descriptive-title.md`. The date MUST use dashes; the rest SHOULD be lowercase with hyphens (avoid underscores).
- Choose names that reflect the problem or topic, not the team or author.
- Example: `2025-06-20-api-migration-guide.md`.
- Place the file in the appropriate folder before committing.

### Timeless vs. Dated

- Docs fall into two buckets:
  - **Timeless general documents** describe enduring processes or repo-wide rules. They do not carry a date prefix and keep their canonical names.
  - **All other content** (design notes, incidents, feature guides, migrations, meeting notes, etc.) must use the date-prefixed naming pattern above with a lower-case, hyphenated title.
- When adding or reviewing documentation, decide which bucket applies. If the doc is not a long-lived reference, rename or relocate it so the filename uses the `YYYY-MM-DD-…` form before merging.

## Required Front Matter

Every doc **must** start with YAML front matter:

```yaml
---
date: 2025-10-24 # From `date +%Y-%m-%d`
author: Name <email@example.com>
title: Short Descriptive Title
tags: [tag1, tag2] # Optional but recommended
---
```

SimpleDoc Guidelines:

- Keep the `date` value in sync with the filename prefix.
- Use a real contact in `author` (`Name <email>`).
- Choose a concise, action-oriented `title`.
- Populate `tags` when it improves discoverability; omit the line if not needed.

## Daily Logs (SimpleLog)

Use SimpleLog for daily logs. The spec lives at `docs/SIMPLELOG_SPEC.md`.

### Where logs live

- Default location: `docs/logs/YYYY-MM-DD.md`.
- The CLI writes to `<repo-root>/docs/logs/` by default when inside a git repo.
- You can set a shared default in `simpledoc.json` and override locally in `.simpledoc.local.json` (see `docs/SIMPLEDOC_CONFIG_SPEC.md`).

### Create a daily log entry (recommended)

Use the CLI to create the file and append entries:

```bash
simpledoc log "Entry text here"
```

Notes:

- The CLI creates the daily log file if missing, including required frontmatter.
- It adds a new session section only when the threshold is exceeded (default 5 minutes).
- It preserves the text you type and inserts a blank line before each new entry.

### Multiline entries

Pipe or heredoc input (stdin) for multiline entries:

```bash
cat <<'EOF' | simpledoc log
Multiline entry.
- line two
- line three
EOF
```

You can also use `--stdin` explicitly:

```bash
simpledoc log --stdin <<'EOF'
Another multiline entry.
EOF
```

### Manual edits (if needed)

- Keep the YAML frontmatter intact (`title`, `author`, `date`, `tz`, `created`, optional `updated`).
- Ensure a blank line separates entries.
- Session sections must be `## HH:MM` (local time of the first entry in that section).

### Ongoing logging (agent behavior)

Once this skill is active in a repo, the agent SHOULD log anything worth noting as it goes. This includes:

- Significant changes, decisions, discoveries, tradeoffs, and assumptions.
- Ongoing progress and small but real steps (changes, commands, tests, doc updates).
- Errors, failures, workarounds, and clarifications.

Log each entry after completing the step or realizing the insight.

## Final Checks Before Submitting

- [ ] Filename follows the `YYYY-MM-DD-…` pattern (date uses dashes) and lives in the correct directory.
- [ ] Capitalized multi-word filenames use underscores (e.g., `CODE_OF_CONDUCT.md`).
- [ ] Timeless vs. dated classification is correct and filenames reflect the choice.
- [ ] Front matter is complete and accurate.
- [ ] Links to related documentation exist where applicable.
- [ ] Run `npx -y @simpledoc/simpledoc check` (or `simpledoc check`) to verify SimpleDoc conventions.
