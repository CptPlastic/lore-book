# Changelog

## v1.4.4 - 2026-04-07

### Other
- Add re-entry guard to git hooks
- Merge branch 'main' of https://github.com/CptPlastic/lore-book
- Document CLI additions and CHRONICLE updates

## v1.4.3 - 2026-04-07

### Fixes
- use PYTHONPATH-based version check to avoid quote parsing errors
- detect nested sdist root before pip install

### Other
- Add association automation and CLI commands
- Merge branch 'main' of https://github.com/CptPlastic/lore-book
- Merge branch 'main' of https://github.com/CptPlastic/lore-book
- Add auto-update and CHRONICLE sync daemon

## v1.4.2 - 2026-04-05

### Features
- add memory association flow to TUI and onboarding/docs guidance
- auto-link related memories via semantic suggestions

### Fixes
- publish exact built artifacts and avoid duplicate PyPI builds
- install from local payload and fail on version mismatch

## v1.4.1 - 2026-04-05

### Features
- surface memory dependencies in detail view and add global dependency map

### Fixes
- correct lore-book 1.4.0 sdist hash

### Other
- Add 1.4.0 Context Keeper docs
- v1.4.1 - TUI dependency visualization

## v1.4.1 - 2026-04-05

### Features
- TUI enhancements — surface memory dependencies in detail view and add global dependency map
	- DetailScreen now displays DEPENDS, RELATED, USED BY, REVIEW, DEPRECATED fields
	- New DependencyMapScreen (accessed via 'g' key) shows all depends_on edges at a glance
	- Reference resolution displays target memory categories for quick context

## v1.4.0 - 2026-04-05

### Features
- Phase 1 context keeper — metadata, lint, trust history, extraction patterns

### Other
- Merge branch 'main' of https://github.com/CptPlastic/lore-book
- Bump scoop to 1.3.1 and enhance packaging script

## v1.3.1 - 2026-03-26

### Other
- Import existing CHRONICLE during onboarding
- install to app-local site and set PYTHONPATH
- Add Scoop bucket sync workflow; remove template
- Add Scoop bucket template and docs
- Add Windows packaging & installer support

## v1.3.0 - 2026-03-25

- Maintenance release.

## v1.2.11 - 2026-03-25

### Other
- Remove commit validation; update CHRONICLE
- Merge branch 'main' of https://github.com/CptPlastic/lore-book
- Add PyPI publish job and CHRONICLE notes

## v1.2.10 - 2026-03-25

### Documentation
- add demo/overview presentation page

### Other
- Merge branch 'main' of https://github.com/CptPlastic/lore-book
- Add CHRONICLE sync & automated releases
- Add demo slide deck (site/demo.html)

