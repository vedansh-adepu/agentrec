# Public Release Checklist

This checklist gates any decision to make agentrec public. Repository visibility must not change without explicit owner approval.

## Required Before Public Visibility

- [x] CI is green on GitHub Actions.
- [x] README is accurate for the current offline MVP.
- [ ] Confirm no secrets, API keys, or `.env` files are tracked.
- [ ] Confirm no generated private `runs/` data is tracked.
- [ ] Confirm the CLI demo works from a clean local setup.
- [x] Current limitations are documented honestly.
- [ ] License decision is made.
- [ ] Repository visibility change is explicitly approved by the owner.

## Optional Future Polish

- [ ] Add MIT license if approved.
- [ ] Add a README badge if desired.
- [ ] Add richer demo screenshots or terminal captures later.
- [ ] Add live provider adapters later.

## Notes

- The repository remains private for now.
- The current MVP is offline-only and uses a fake model provider plus calculator tool.
- Public release should not imply live OpenAI, Anthropic, LangChain, or LangGraph support until those integrations are implemented and tested.
