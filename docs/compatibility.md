# Compatibility and portability

Venturemorph is a directory-based instruction skill. Its portable core is `skills/venturemorph/SKILL.md`, with supporting references, a state template, and optional validation. The core workflow needs an agent that can read and follow these instructions; it does not require a service or code runtime.

## Supported ways to use it

| Environment | Setup | Invocation and continuity |
| --- | --- | --- |
| Claude Code, local sessions | Copy `skills/venturemorph` into `~/.claude/skills/venturemorph`; use the collision-safe examples in the [README](../README.md#install-in-claude-code). | Invoke `/venturemorph`. Keep state in the project being reviewed and provide it on subsequent reviews. |
| ChatGPT, with attachments | Attach `SKILL.md`, all four reference files, the review and state templates, and the latest project state/evidence. The checker is optional if Python execution is available; see the [exact checklist](../README.md#use-with-chatgpt-and-other-agents). | Explicitly ask ChatGPT to follow the attached workflow. Transfer updated state manually between sessions when needed. |
| ChatGPT/Codex workspace with native skills | Follow the workspace's current product instructions to install the complete skill folder, if supported. | Host capabilities determine discovery, invocation, persistence, and tool access. `agents/openai.yaml` supplies host-facing metadata where recognized. |
| Other Agent Skills hosts | Install the complete skill folder according to the host's documentation. | Confirm that the host reads supporting files and can return or save updated state. Do not assume Claude-specific commands apply. |

Claude Code's personal folder is local to the machine. Cowork and cloud sessions have separate skill-loading rules; follow the official Claude documentation for those environments.

This describes a portable instruction format, not a guarantee that every host implements native skill installation. Attachment use does not grant file access, browse the web, or create persistent memory by itself. There is no universal ZIP-upload installation flow and no automatic synchronization between Claude, ChatGPT, Codex, or other hosts.

## What travels with the skill

- `SKILL.md` defines the workflow and its evidence rules.
- `references/` provides supporting guidance. Preserve relative paths when installing the directory.
- `assets/project-state.template.json` provides a starting point for a new project's state; `assets/project-state.example.json` illustrates a fictional populated state.
- `assets/review.template.md` provides the report scaffold.
- `LICENSE` preserves the MIT notice when the skill folder is copied separately.
- `agents/openai.yaml` contains ChatGPT/Codex-facing display and prompt metadata. It is not required for the instruction workflow and does not make every host install the skill automatically.
- `scripts/check_state.py` is an optional Python standard-library checker. The agent can run the core review without it.

Copy the `skills/venturemorph` directory itself, rather than the repository root, into a host's skill location. Repository documentation, tests, and git metadata are not needed to run the review.

## What travels with the project

Project state belongs in `.venturemorph/<project-id>/state.json` inside the project being reviewed. The project ID should remain stable across handoffs so that unrelated ventures are not merged by accident. Keep the state private; add `.venturemorph/` to the consumer project's `.gitignore` unless intentionally publishing a sanitized copy.

To change platforms:

1. Ask for a handoff with the latest state, evidence references, unresolved questions, and proposed versus accepted decisions. Keep the full experiment protocol and agreement status in its dated review snapshot; a structurally valid compact experiment object alone cannot preserve every test condition.
2. Review and remove secrets, personal information, or confidential material that the next platform should not receive.
3. Give the destination agent the skill instructions, relevant references, and this latest state. Explain any changes made after the handoff.
4. Ask the agent to compare current evidence with that state before giving new advice. A handoff-only request preserves the existing strategy; it does not authorize a new one.

Avoid editing separate copies in parallel. If two copies have diverged, compare their timestamps and decision history, resolve the differences explicitly, and designate the current copy before continuing. A template or installation is not a substitute for the latest state.

## Tool and evidence limits

Host tools determine whether Venturemorph can read local project files, browse sources, run the checker, or save a state file. If a capability is unavailable, supply the relevant information manually and have the agent return the updated state for you to save.

Source access also affects what can be claimed. An inaccessible dashboard is not evidence of performance. A proposed feature is not shipped. Generating a brand candidate does not confirm availability, legal clearance, or uniqueness. Real availability checks remain limited to their cited source, time, and scope. Missing measurements and untested assumptions must remain visible in the review.

The optional checker validates structure rather than business truth:

```bash
python skills/venturemorph/scripts/check_state.py path/to/state.json
```

Use the local Python launcher appropriate to your environment if `python` is not available under that name. No third-party Python packages are required by the checker.

## Official references

Checked on **2026-11-13**:

- [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/skills) — personal skill location, directory installation, and `/skill-name` invocation.
- [Agent Skills specification](https://agentskills.io/specification) — `SKILL.md`, frontmatter, and supporting directory conventions.

These sources establish the format and Claude Code behavior. They do not establish universal ChatGPT installation support. Follow the current instructions for the specific product and workspace you use.
