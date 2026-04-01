# Changelog

Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`<major>`.`<minor>`.`<patch>`)

## `[v1.2.1]`

### Added

* #17 Provide feedback in the terminal if no workflows are discovered at the given root

### Fixed

* #18 Sort results of release query by version number instead of release date

## `[v1.2.0]`

### Changed

* (Internal) Moved network related functionality to asynchronous calls

### Added

* Add support for specifying API key in `.env`

## `[v1.1.0]`

### Changed

* #5 CLI execution has been split into `local` and `remote` subcommands; `CheckWorkflow remote <...>` now provides the previous functionality

### Added

* #5 Add parsing of local project workflows using `CheckWorkflow local <...>`

## `[v1.0.0]`

Initial release 🎉
