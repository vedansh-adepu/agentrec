# Public Release Checklist

This checklist records the public release readiness checks for agentrec.

## Required Before Public Visibility

- [x] CI is green on GitHub Actions.
- [x] README is accurate for the current offline MVP.
- [x] Confirm no secrets, API keys, or `.env` files are tracked.
- [x] Confirm no generated private `runs/` data is tracked.
- [ ] Confirm the CLI demo works from a clean local setup.
- [x] Current limitations are documented honestly.
- [x] License decision is made: MIT.
- [x] `LICENSE` file is added.
- [x] Repository visibility change is explicitly approved by the owner.
- [x] Repository visibility changed to public.

## Optional Future Polish

- [x] Add MIT license if approved.
- [ ] Add a README badge if desired.
- [ ] Add richer demo screenshots or terminal captures later.
- [ ] Add live provider adapters later.

## Notes

- The repository is now public: `https://github.com/vedansh-adepu/agentrec`.
- The MIT License has been selected and added.
- The final visibility check found no secrets, `.env` files, generated runs, virtualenvs, cache folders, or temporary/log files.
- The current MVP is offline-only and uses a fake model provider plus calculator tool.
- Public release should not imply live OpenAI, Anthropic, LangChain, or LangGraph support until those integrations are implemented and tested.
