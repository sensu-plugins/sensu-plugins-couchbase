#Change Log
This project adheres to [Semantic Versioning](http://semver.org/).

This CHANGELOG follows the format listed at [Keep A Changelog](http://keepachangelog.com/)

## [Unreleased]

## [0.2.0] - 2015-11-20
### Added
- add couchbase cluster check
- add couchbase bucket replica check
- metrics-couchbase.py: add ep_cache_miss_rate metric

### Changed
- Switched to rest-client

### Fixed
- check-couchbase-bucket-quota.rb: Fixed issue when only last bucket was shown in the output and/or check stopped on
  the first problem found


## [0.1.0] - 2015-08-11
### Added
- add metrics-couchbase.py plugin (requires python requests,DNS modules)

## [0.0.3] - 2015-07-14
### Changed
- updated sensu-plugin gem to 1.2.0

## [0.0.2] - 2015-06-02
### Fixed
- added binstubs

### Changed
- removed cruft from /lib

## 0.0.1 - 2015-05-04
### Added
- initial release

[unreleased]: https://github.com/sensu-plugins/sensu-plugins-couchbase/compare/0.2.0...HEAD
[0.2.0]: https://github.com/sensu-plugins/sensu-plugins-couchbase/compare/0.1.0...0.2.0
[0.1.0]: https://github.com/sensu-plugins/sensu-plugins-couchbase/compare/0.0.3...0.1.0
[0.0.3]: https://github.com/sensu-plugins/sensu-plugins-couchbase/compare/0.0.2...0.0.3
[0.0.2]: https://github.com/sensu-plugins/sensu-plugins-couchbase/compare/0.0.1...0.0.2
