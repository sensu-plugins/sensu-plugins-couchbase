#! /usr/bin/env ruby
#
#   check-couchbase-bucket-replica
#
# DESCRIPTION:
#   This plugin checks Couchbase bucket replication number.
#
# OUTPUT:
#   plain text
#
# PLATFORMS:
#   Linux
#
# DEPENDENCIES:
#   gem: sensu-plugin
#   gem: rest-client
#   Gem: json
#
# USAGE:
#   check-couchbase-bucket-replica.rb -u admin -P secret -a http://<ip>:8091 -r 3
#   check-couchbase-bucket-replica.rb -u admin -P secret -a http://<ip>:8091 -b superreplica -r 5
#
# NOTES:
#   This plugin is tested against couchbase 3.0.x
#
# LICENSE:
#   Copyright (c) 2015, Olivier Bazoud, olivier.bazoud@gmail.com
#   Released under the same terms as Sensu (the MIT license); see LICENSE
#   for details.
#

require 'sensu-plugin/check/cli'
require 'rest-client'
require 'json'

#
# Check Couchbase
#
class CheckCouchbaseBucketReplica < Sensu::Plugin::Check::CLI
  option :user,
         description: 'Couchbase Admin Rest API auth username',
         short: '-u USERNAME',
         long: '--user USERNAME'

  option :password,
         description: 'Couchbase Admin Rest API auth password',
         short: '-P PASSWORD',
         long: '--password PASSWORD'

  option :api,
         description: 'Couchbase Admin Rest API base URL',
         short: '-a URL',
         long: '--api URL',
         default: 'http://localhost:8091'

  option :replica,
         description: 'Replication number expected',
         short: '-r REPLICA',
         long: '--replica REPLICA',
         proc: proc(&:to_f),
         default: 1

  option :bucket,
         description: 'Bucket name, if ommited all buckets will be checked',
         short: '-b BUCKET',
         long: '--bucket BUCKET'

  def run
    begin
      resource = '/pools/default/buckets'
      response = RestClient::Request.new(
        method: :get,
        url: "#{config[:api]}/#{resource}",
        user: config[:user],
        password: config[:password],
        headers: { accept: :json, content_type: :json }
      ).execute
      results = JSON.parse(response.to_str, symbolize_names: true)
    rescue Errno::ECONNREFUSED
      unknown 'Connection refused'
    rescue RestClient::ResourceNotFound
      unknown "Resource not found: #{resource}"
    rescue RestClient::RequestFailed
      unknown 'Request failed'
    rescue RestClient::RequestTimeout
      unknown 'Connection timed out'
    rescue RestClient::Unauthorized
      unknown 'Missing or incorrect Couchbase REST API credentials'
    rescue JSON::ParserError
      unknown 'couchbase REST API returned invalid JSON'
    end

    results.each do |bucket|
      next if config[:bucket] && bucket[:name] != config[:bucket]

      message "Couchbase #{bucket[:name]} bucket replica number is #{bucket[:replicaNumber]}"
      critical if bucket[:replicaNumber] != config[:replica]
    end

    ok "Couchbase buckets replica number is #{config[:replica]}"
  end
end
