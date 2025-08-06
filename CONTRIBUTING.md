# Contributing to Gemma Sullivan Project

Thanks for taking the time to contribute — every improvement helps us bring quality, offline-first education to more learners.

## Before you start

1. Read the project [README](./README.md) to understand goals and structure (student app, tutor app, docs).  
2. Search [Issues](../../issues) to avoid duplicates.  
3. Be respectful and constructive. We value clear, kind communication.

## How to report a bug

Provide enough detail so someone else can reproduce the problem.

**Include (when relevant):**

- What you did and what you expected to happen.
- Exact steps to reproduce (numbered).
- Screenshots or logs if helpful.
- Environment details: OS, device, Python/Node versions, and which app (`student-app` or `tutor-app`).

**Then:**

1. Open a new issue: [New Bug]([../../issues/new?labels=bug](https://github.com/DavidLMS/gemma-sullivan-project/issues/new?assignees=&labels=bug&projects=&template=bug_report.md&title=%5BBUG%5D)).  
2. Keep one problem per issue.  
3. If the issue is security‑sensitive, avoid posting secrets or keys in public. Remove private data from logs.

## Suggesting enhancements

Great ideas are welcome! Please:

- Describe the current behavior and the proposed change.
- Explain the use case: who benefits and why (tie it to offline-first, accessibility, or learning impact when possible).
- List alternatives you considered.
- Add mockups or small diagrams if UI/UX is affected.

Open here: [New Feature](../../issues/new?labels=enhancement).

## Your first code contribution

1. **Fork** this repo and create a feature branch:  
   ```bash
   git checkout -b feat/my-change
   ```
2. **Make small, focused commits.** Prefer several small PRs over one giant PR.
3. **Run locally & self‑test.** Make sure your changes work for the target app(s).

## Pull Request checklist

- The PR title is descriptive (use *imperative* mood).  
- The scope is minimal and focused (ideally < ~300 lines of diff).  
- Tests pass and new ones are added when needed.  
- Docs are updated (README, comments, usage guides).  
- UI changes include screenshots or a brief demo.  
- No secrets or keys in code or history.

Once opened, be responsive to feedback. We try to review promptly.

## Commit messages

Use clear, concise messages. Conventional Commits are welcome:
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation
- `test:` tests
- `refactor:` internal changes
- `chore:` tooling or housekeeping

Example: `feat(student-app): add offline cache warmup flow`

## Style & architecture tips

- Prefer small, composable modules and pure functions.
- Keep UX accessible (keyboard, screen readers, clear copy).
- Favor resilience and low resource usage (battery/network) — it’s an offline‑first project.

## License

By contributing, you agree that your contributions are licensed under this repository’s license: **CC BY 4.0** (see [`LICENSE`](./LICENSE)).

## Code of Conduct (short version)

Be kind. Assume good intent. No harassment or discrimination. Respect different backgrounds and constraints, especially from communities with limited connectivity.

If something goes wrong, let the maintainers know in an issue.

## Thank you

If you don’t have time to contribute code, you can still help:
- Star the repo.
- Share it with educators and NGOs.
- File docs or usability issues when something is confusing.
