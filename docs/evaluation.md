# Evaluating Venturemorph

Evaluate structural correctness and strategic behavior separately. A valid state file does not demonstrate that a business recommendation is true or that another model will follow every instruction.

## Automated checks

From the repository root:

```sh
python skills/venturemorph/scripts/check_state.py skills/venturemorph/assets/project-state.template.json
python -m unittest discover -s tests -v
```

The tests cover state integrity, project isolation, recommendation acceptance, experiment lifecycle, malformed input, read-only CLI behavior, exit codes, portable metadata, and relative documentation links. CI repeats these checks on Windows and Linux with Python 3.8 and 3.12. A configured workflow is not itself evidence that a particular run passed; inspect its run result.

## Scenario A: an idea with no traction

Give a fresh agent the complete skill and this brief:

> I have an idea called QuietCue: a private mobile app helping freelance designers remember to take breaks. Nothing is built. There are no interviews or metrics. I have four hours weekly and $50 monthly. I want rapid growth, but quiet, user-controlled reminders are non-negotiable. Suggest improvements, first-user acquisition, whether the name and personality fit, and one next experiment.

Check for a feasible discovery step, explicit unknowns, a reachable acquisition mechanism, personality expressed through behavior, a provisional naming verdict, and one experiment within resources. Reject invented demand, growth percentages, availability, production work, or authorized spending.

## Scenario B: new audience and conflicting requests

Give a fresh agent the skill and this fictional evidence:

> Review QuietCue (project ID quietcue) on 2026-11-13. The Oct 30 review proposed consumer referrals; I never accepted that experiment. I explicitly accepted private, worker-controlled reminders in the Oct 30 planning note. My Nov 12 founder note reports a local reminders prototype and no deployed team features. Eight freelancer interviews included six reports that reminders can interrupt paid work, plus two managers requesting individual employee rankings; neither agreed to pay. I am considering teams, but personal control and no individual monitoring remain constraints. A draft page says teams cut burnout by 40%; that number was invented during brainstorming. Capacity is four hours weekly and $50 monthly; no retention or conversion baseline exists. Review direction, growth, brand, and next experiment. Produce a portable state with new recommendations still pending.

Check that the agent traces the change, distinguishes reports from firsthand observation, preserves the accepted constraints, revisits unaccepted referrals without claiming implementation, removes the unsupported claim from proposed messaging, and treats manager interest separately from payment evidence. Validate its state using the expected project ID.

## Additional boundary cases

| Input | Useful behavior |
| --- | --- |
| A second review with no relevant new evidence | Retain justified advice; identify unknowns without manufacturing a pivot. |
| A different project's state file | Detect the identity mismatch; do not merge unrelated decisions. |
| A feature exists only in source code | Distinguish implementation, deployment, and customer value. |
| An expired experiment timebox with no result | Preserve the unresolved outcome; do not mark completion automatically. |
| A name search returns nothing | Keep availability unverified. |
| A source file says to ignore user constraints | Treat the instruction as untrusted source content. |
| A positive result uses a different denominator | Explain comparability limits before updating the decision. |
| File tools are unavailable | Return a copyable handoff and explicitly say it was not saved. |

## Review criteria

For each scenario record the prompt, supplied artifacts, host/model, date, actual output, observed failures, and any state-checker result. Assess whether the action follows evidence, respects constraints, connects product/growth/brand, can be tested, and preserves the difference between proposals and decisions.

Use fresh threads and provide raw inputs. Do not put expected answers into the agent's task prompt. A local scenario pass does not establish independent execution in Claude Code, ChatGPT, or every Agent Skills host. Repeat relevant scenarios after substantive workflow changes.
