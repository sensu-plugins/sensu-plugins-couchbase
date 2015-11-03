#! /usr/bin/env ruby
#
#   check-couchbase-cluster
#
# DESCRIPTION:
#   This plugin checks Couchbase cluster.
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
#
# NOTES:
#   This plugin is tested against couchbase 3.0.1
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
# Check Couchbase cluster
#
class CheckCouchbaseCluster < Sensu::Plugin::Check::CLI
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

  option :cluster_size,
         description: 'Cluster size expected',
         short: '-c CLUSTER_SIZE',
         long: '--cluster-size CLUSTER_SIZE',
         proc: proc(&:to_f)

  option :couchbase_version,
         description: 'Couchbase version expected',
         short: '-v VERSION',
         long: '--version VERSION',
         proc: proc(&:to_f)

  def run
    begin
      resource = '/pools/nodes'
      response = RestClient::Request.execute(
        method: :get,
        url: "#{config[:api]}/#{resource}",
        user: config[:user],
        password: config[:password],
        headers: { accept: :json, content_type: :json }
      )
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

    critical "Cluster's size is #{results[:nodes].size}, #{config[:cluster_size]} expected" if results[:nodes].size != config[:cluster_size]

    if config[:couchbase_version]
      nodes_version = results[:nodes].select { |node| node[:version] != config[:couchbase_version] }
      critical "Unexpected couchbase's version on nodes: #{nodes_version.map { |node| node[:hostname] }}" if nodes_version.size > 0
    end

    nodes_unhealthy = results[:nodes].select { |node| node[:status] != 'healthy' }
    critical "These nodes are not 'healthy': #{nodes_unhealthy.map { |node| node[:hostname] }}" if nodes_unhealthy.size > 0

    nodes_unactive = results[:nodes].select { |node| node[:clusterMembership] != 'active' }
    critical "These nodes are not 'active' in the cluster: #{nodes_unactive.map { |node| node[:hostname] }}" if nodes_unactive.size > 0

    critical "Cluster #{results[:alerts].size} alert(s)" if results[:alerts].size > 0

    warning "Cluster rebalance status #{results[:rebalanceStatus]}" if results[:rebalanceStatus] != 'none'

    ok "Nodes: #{results[:nodes].size}"
  end
end
