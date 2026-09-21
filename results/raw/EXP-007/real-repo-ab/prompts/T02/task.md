You are working in an isolated benchmark fixture of HermesMobile.

**Goal:** Repair a reconnect/recovery regression.

A user can background or kill the app while a Hermes run is in progress. If the gateway later no longer retains that run record, but the assistant answer is already present in the session transcript, reopening the app must recover and display that answer in the correct profile/session.

A focused regression test has been added and currently fails. Work directly in the repository: inspect the controller, its dependency seams, and the test; identify the real lifecycle cause; make the smallest correct repair; then run the focused test and the relevant deterministic suite. Do not start services or change dependencies. Finish with a concise summary and exact verification results.
