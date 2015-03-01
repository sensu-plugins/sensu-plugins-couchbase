## Sensu-Plugins-disk-checks

[![Build Status](https://travis-ci.org/sensu-plugins/sensu-plugins-couchbase.svg?branch=master)](https://travis-ci.org/sensu-plugins/sensu-plugins-conntrack)
[![Gem Version](https://badge.fury.io/rb/sensu-plugins-conntrack.svg)](http://badge.fury.io/rb/sensu-plugins-conntrack)
[![Code Climate](https://codeclimate.com/github/sensu-plugins/sensu-plugins-conntrack/badges/gpa.svg)](https://codeclimate.com/github/sensu-plugins/sensu-plugins-conntrack)
[![Test Coverage](https://codeclimate.com/github/sensu-plugins/sensu-plugins-conntrack/badges/coverage.svg)](https://codeclimate.com/github/sensu-plugins/sensu-plugins-conntrack)
[![Dependency Status](https://gemnasium.com/sensu-plugins/sensu-plugins-conntrack.svg)](https://gemnasium.com/sensu-plugins/sensu-plugins-conntrack)
## Functionality

## Files
 * bin/check-couchbase-bucket-quota

## Usage

## Installation

Add the public key (if you haven’t already) as a trusted certificate

```
gem cert --add <(curl -Ls https://raw.githubusercontent.com/sensu-plugins/sensu-plugins.github.io/master/certs/sensu-plugins.pem)
gem install sensu-plugins-couchbase -P MediumSecurity
```

You can also download the key from /certs/ within each repository.

#### Rubygems

`gem install sensu-plugins-couchbase`

#### Bundler

Add *sensu-plugins-disk-checks* to your Gemfile and run `bundle install` or `bundle update`

#### Chef

Using the Sensu **sensu_gem** LWRP
```
sensu_gem 'sensu-plugins-couchbase' do
  options('--prerelease')
  version '0.0.1.alpha.4'
end
```

Using the Chef **gem_package** resource
```
gem_package 'sensu-plugins-couchbase' do
  options('--prerelease')
  version '0.0.1.alpha.4'
end
```

## Notes

[1]:[https://travis-ci.org/sensu-plugins/sensu-plugins-couchbase]
[2]:[http://badge.fury.io/rb/sensu-plugins-couchbase]
[3]:[https://codeclimate.com/github/sensu-plugins/sensu-plugins-couchbase]
[4]:[https://codeclimate.com/github/sensu-plugins/sensu-plugins-couchbase]
[5]:[https://gemnasium.com/sensu-plugins/sensu-plugins-couchbase]
