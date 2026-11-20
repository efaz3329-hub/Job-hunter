---
description: Sort unlabelled mail into labels in logged, reversible passes, and generate Gmail filters
argument-hint: "[learn | pass | filters | undo <n>]"
---

Load the `label-organizer` skill.

- `learn`: build or refresh the label rules from how the owner has already labelled mail.
- `pass` (default): run one labelling pass of 200-300 threads, after showing the plan.
- `filters`: write `work/mailFilters.xml` for import in Gmail settings.
- `undo <n>`: show and, on approval, apply the reverse of pass n from the undo log.
