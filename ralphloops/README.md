# `ralphloops/` — staging area for ralphloops.io and ralphloops/ralphloops

This directory is a **staging area** for the Ralph Loops project. It
contains two things that will eventually move to their own homes:

- **[`website/`](website/)** — the static site for
  [ralphloops.io](https://ralphloops.io/). Minimal, technical,
  inspired by [agentskills.io](https://agentskills.io/).
- **[`repo/`](repo/)** — the contents of the future
  `ralphloops/ralphloops` GitHub repository: specification, creator
  docs, implementor docs, example loop packages, JSON Schema,
  conformance fixtures, RFCs, and governance.

## Why it lives here for now

The `ralphloops` GitHub organization and repo do not exist yet. This
subdirectory lets us develop the format, the spec, and the site
alongside Ralphify (one reference implementation) until we're ready
to move it out.

When the `ralphloops` org is created:

1. Copy `ralphloops/repo/` into the new `ralphloops/ralphloops` repo.
2. Deploy `ralphloops/website/` to the ralphloops.io domain.
3. Remove this staging directory from the Ralphify repo.

## Positioning

Ralph Loops is positioned everywhere as:

> **An open proposed format for portable Ralph-style agent loops.**

- It is **not** a standard.
- It is **not** a Ralphify feature.
- It is **inspired by** Geoffrey Huntley's Ralph loop methodology and
  does not claim ownership of that methodology.
- Ralphify is **one reference runtime** for the format, not the
  format itself.

## Layout

```
ralphloops/
├── README.md              # this file
├── website/               # ralphloops.io static site
│   ├── index.html
│   ├── styles.css
│   ├── specification/
│   ├── loop-creation/
│   │   ├── quickstart/
│   │   └── best-practices/
│   ├── implementors/
│   │   ├── overview/
│   │   └── reference/
│   ├── examples/
│   └── governance/
└── repo/                  # ralphloops/ralphloops repo contents
    ├── README.md
    ├── LICENSE
    ├── CONTRIBUTING.md
    ├── CODE_OF_CONDUCT.md
    ├── GOVERNANCE.md
    ├── VERSIONING.md
    ├── specification/
    ├── loop-creation/
    ├── implementors/
    ├── examples/          # six reference loop packages
    ├── schemas/
    ├── tests/             # conformance corpus
    ├── rfcs/
    └── .github/
```
