---
mode: agent
description: Review an existing CR spec or workbook against the framework rules before it goes to the reviewers.
---

# Review a CR estimate

Check a spec (and the workbook built from it) the way the estimate reviewer
will. Read `docs/estimation-rules.md` first.

Ask me which spec to review if I have not said.

## Run the tool's own checks first

```bash
cr-tool validate <spec.json>
```

Report every warning it prints. Then work through what the tool cannot judge:

## Consistency

- Does the dimension prefix in each column D block match the flags set for that
  row? `MS (Complex)` in the prose but `"ms": [0,1,0]` in the flags is the most
  common defect.
- Does every non-`Shared` `user_story` in `rows` appear as a `us_id` in
  `stories`, and vice versa?
- Does each `Shared` row sit in the right group?

## Coverage

- Is every AC in the source user stories represented by some Details row?
  Name any AC that is not.
- Does every screen in the Figma pack map to either a UI flag or an explicit
  note that it is unchanged?
- Are the TSP `details` counts consistent with the sizes chosen? A `Small (1-3)`
  with five items listed underneath is wrong.

## Calibration

- Any row above 10 MD, or carrying more than 3 flags — should it be split?
- Any row at 1–2 MD that is quietly doing a lot — is it under-flagged?
- Are the reusability levels defensible against the ladder in the rules doc,
  given what the HLD actually says?
- Is `Not Applicable` used where a dimension is genuinely untouched, rather than
  `0 - No Reusability`? They mean different things and score differently.

## Specificity

- Is every endpoint labelled new vs existing?
- Is BPM impact stated explicitly, even when it is `none`?
- Are there `[TBD]` markers that should have been resolvable from the input pack?

## Output

Give me a findings list ordered most-serious first. For each: the row, what is
wrong, and the concrete correction. If everything is sound, say so plainly and
give me the totals. Do not rewrite the spec unless I ask.
