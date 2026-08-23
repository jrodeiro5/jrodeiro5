---
title: Manual Overview
topics: [manual]
---

# Manual Overview

This manual defines how agents maintain a CodeAlmanac repo-owned wiki.

Prompts name the run. The manual explains how to write the pages.

Read the relevant page before editing:

- [How To Write](how-to-write) — the general writing standard for all pages.
- [Evidence](evidence) — how claims stay grounded and how conflicts are handled.
- [Links](links) — how wiki pages and hubs connect.
- [Topics](topics) — how topic graphs support querying and browsing.
- [Concepts](concepts) — how to write concept pages.
- [Architecture](architecture) — how to write architecture pages.
- [How-To Guides](how-to-guides) — how to write task guides.
- [Decisions](decisions) — how to write decision pages.
- [Reference](reference) — how to write reference pages.
- [Sources](sources) — how raw material relates to wiki synthesis.
- [Ingest](ingest) — how to fold new material into an existing wiki.
- [Garden](garden) — how to improve an existing wiki graph.

Repo-specific conventions live in `almanac/README.md` and
`almanac/topics.yaml`.

## Folder Structure

The only repo wiki root is `almanac/`. The committed wiki source is a
browseable Markdown tree.

```text
almanac/
|-- README.md
|-- topics.yaml
|-- concepts/
|   `-- sources.md
|-- architecture/
|   |-- README.md
|   `-- indexing.md
|-- decisions/
|   `-- local-first.md
|-- guides/
|   `-- setup.md
`-- reference/
    `-- page-format.md
```

`almanac/README.md` plus `almanac/topics.yaml` identify an initialized
CodeAlmanac wiki.

The category folders are the default first-build structure. Do not add
`active/`, `_meta/`, or `context/` during build unless repository evidence
makes that structure necessary.

Runtime state is local and rebuildable:

```text
~/.codealmanac/codealmanac.db
~/.codealmanac/repos/<repo-id>/index.db
```

The local database records repositories, runs, run events, worker locks, and
sync state. Per-repository runtime files contain derived indexes. They are not
wiki source.
