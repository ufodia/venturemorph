# Contributing to Venturemorph

Venturemorph helps an agent reconsider product, growth, and brand decisions as a project changes. Contributions should make that workflow more useful, clear, and portable without turning it into a framework that requires a service or runtime.

## Useful contributions

- Clearer instructions for comparing project versions and revising prior advice.
- Better handling of incomplete, contradictory, or weak evidence.
- Examples that connect a product change to a growth constraint and brand decision.
- State validation fixes, focused tests, and documented compatibility corrections.

For a bug report, include the relevant instruction, expected behavior, actual behavior, and a small sanitized example. For a change in behavior, explain the problem and the decision your proposal helps the user make. Keep private project state, credentials, customer details, and confidential source material out of issues and pull requests.

## Preserve the workflow's commitments

Changes must keep planned and shipped work separate, label hypotheses and facts, and distinguish proposed recommendations from user-accepted decisions. Preserve evidence provenance and uncertainty. Do not replace missing baselines with invented metrics or claim that a brand name is available, legally cleared, perfect, or unique.

The standard review should still deliver up to three prioritized improvements, one measured experiment, and a keep/evolve/rename brand verdict. Earlier advice should be revised when the evidence changes, with the reason recorded rather than silently rewritten.

Keep the core instructions usable without Python. Add optional scripts only when they provide a concrete benefit, document their requirements, and prefer the standard library. Avoid host-specific behavior in the portable core; explain host differences in `docs/compatibility.md`.

## Make a change

1. Create a focused branch from the current default branch.
2. Update the relevant files under `skills/venturemorph/` and any affected documentation.
3. If changing the state format, update the template, checker, and relevant tests together. Explain how existing state should be handled; do not silently discard decisions or evidence.
4. Run the checks below and review the resulting diff for private data and unintended changes.
5. Open a pull request describing the problem, resulting behavior, and validation performed. State any checks you could not run.

From the repository root:

```bash
python -m unittest discover -s tests -v
python skills/venturemorph/scripts/check_state.py skills/venturemorph/assets/project-state.template.json
```

For workflow changes, also walk through a realistic before-and-after scenario. Confirm that previous advice is reconsidered, unshipped work remains labeled, uncertain evidence stays uncertain, and a proposed decision is not promoted to accepted without the user's decision. Automated structure checks cannot establish these qualities on their own.

If you change installation or compatibility claims, verify them against current official documentation and record the verification date. Do not infer native installation support from the mere presence of an Agent Skills folder or `agents/openai.yaml`.

## License

By submitting a contribution, you agree that it may be distributed under this repository's [MIT license](LICENSE).
