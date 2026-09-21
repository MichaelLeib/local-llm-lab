You are working in an isolated benchmark fixture of HermesMobile.

**Goal:** Fix the reported mobile layout regression.

On narrow iPhones:

1. Focusing any user-editable text input must not trigger Safari's automatic page zoom. This includes the chat composer, model-picker search, and dialog text input.
2. Wide assistant Markdown content (especially comparison tables and long code) must never let the entire chat/thread pane pan horizontally. Wide content may scroll **inside its own intended container**.

Work directly in the repository. Inspect relevant code before editing. Make the smallest maintainable fix, add or adjust deterministic tests if appropriate, and run the relevant project checks. Do not start services or change dependencies. Finish with a concise summary of the files changed and exact verification commands/results.
