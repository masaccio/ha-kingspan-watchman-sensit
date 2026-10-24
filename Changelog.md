# What's Changed

🪲 indicates bug fixes
🚀 indicates new features or improvements
🔧 indicates non-user-visible developer improvements

## v2.1.0

🚀 Refactored how exceptions are handled within the integration to improve integration resilience.
🚀 Improved re-authentication and reconfiguration flows for password updates.
🚀 New repair workflow integrates better into recent Home Assistant.
🚀 Updated German translations to [informal imperative mood](https://contributors.home-assistant.io/translate/reference/languages/).
🚀 New French translations (note: GenAI-generated).
🔧 Implemented strict pre-commit hooks for linting and formatting and type-checking.
🔧 Test suite overhaul for improve parameterization and reduce code duplication.

## v2.0.2

🪲 Fixed API tokens [issue-80](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/80) with latest API library.

## v2.0.1

🪲 Fixed translations [issue-67](https://github.com/masaccio/ha-kingspan-watchman-sensit/issues/67) which caused errors in Home Assistant.

## v2.0.0

**The underlying APIs have changed significantly, so this may be an unstable release.**

This is a major update to reflect the API changes introduced by the move to KNECT Pro in February 2026. The underlying API module should be considered experimental as the roll-out of KNECT Pro was sudden and some of the APIs have a very preliminary feel so could easily change in the future. There is no date for when the APIs used by the 1.x Home Assistant integration will be retired, so you may wish to stay on that version. There are no functional differences in the 2.x versions.

🚀 Enabled dependabot to ensure that dependencies are kept up-to-date.
🚀 Multiple stability improvements in API usage.
🚀 Entity names for new integration installations are correctly scoped by tank name (does not affect existing installations).
