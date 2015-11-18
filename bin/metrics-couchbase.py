#!/usr/bin/env python
#
#   metrics-couchbase.py
#
# DESCRIPTION:
# Collects several couchbase stats using the couchbase stats REST API endpoints
#
# OUTPUT:
#   graphite plain text protocol
#
# PLATFORMS:
#   Linux
#
# DEPENDENCIES:
#   python module: requests http://www.python-requests.org
#   python module: pydns http://pydns.sourceforge.net
#
# USAGE:
# metrics-couchbase.py -u <user> -p <pw> -c <cb_host> [-s graphite_scheme] [-d] [-b] [-r]
# NOTES:
# This plugin gets *all* the CB cluster members dynamically and grab all the
# stats it can, in addition it grabs per bucket stats so be prepared for
# lots of stats...On a prod small CB cluster the output is ~5000 metrics.
# LICENSE:
#   Jaime Gago  contact@jaimegago.com
#   Released under the same terms as Sensu (the MIT license); see LICENSE
#   for details.
#

import DNS
import logging
import logging.handlers
import optparse
import requests
import sys
import time
from operator import add

FAILURE_CONSTANT = 1

PER_BUCKET_PER_NODE_STATS = [
    'cas_hits',
    'cmd_get',
    'cmd_set',
    'curr_connections',
    'cpu_utilization_rate',
    'curr_items',
    'decr_hits',
    'decr_misses',
    'delete_misses',
    'delete_hits',
    'ep_bg_fetched',
    'ep_flusher_todo',
    'ep_max_size',
    'ep_mem_high_wat',
    'ep_mem_low_wat',
    'ep_cache_miss_rate',
    'ep_tmp_oom_errors',
    'ep_queue_size',
    'incr_hits',
    'incr_misses',
    'mem_used',
    'ops',
    'vb_active_eject',
    'vb_active_itm_memory',
    'vb_active_meta_data_memory',
    'vb_active_num',
    'vb_active_queue_drain',
    'vb_active_queue_fill',
    'vb_active_queue_size',
    'vb_active_resident_items_ratio',
    'vb_replica_num'
    ]

PER_BUCKET_STATS = [
    'cas_hits',
    'cmd_get',
    'cmd_set',
    'curr_items',
    'decr_hits',
    'decr_misses',
    'incr_hits',
    'incr_misses',
    'ops',
    'vb_active_resident_items_ratio',
    ]

WRITE_STATS = [
    'cmd_set',
    'incr_misses',
    'incr_hits',
    'decr_misses',
    'decr_hits',
    'cas_hits'
    ]

# Helper functions
def set_syslog():
  '''Set a syslog logger'''
  try:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(pathname)s: %(message)s")

    handler = logging.handlers.SysLogHandler(address = '/dev/log')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
  except Exception:
    logging.critical("Failed to configure syslog handler")
    sys.exit(1)
  return logger

def min_med_max_avg(floats):
  '''Return dict with min,median,max,avg(integers) from a list of floats'''
  min_med_max_avg = {}
  # Median calculations
  values = sorted(floats)
  midpoint = len(values) / 2
  if len(values) % 2 == 0:
    med = avg(values[midpoint:midpoint+2])
  else:
    med = values[midpoint]
  min_med_max_avg['min'] = min(floats)
  min_med_max_avg['med'] = med
  min_med_max_avg['max'] = max(floats)
  min_med_max_avg['avg'] = avg(floats)
  return min_med_max_avg

def avg(floats):
  length = len(floats)
  total = sum(floats)
  return total / length

def dns_reverse_lookup(dns_server, timeout_in_sec, ip, logger):
  '''Tries to return a hostname doing a DNS rev lookup'''
  dns_answered = False
  try:
    reversed_ip = '.'.join(ip.split('.')[::-1])
  except Exception as e:
    logger.critical('not a valid IP')
    logger.critical(e)
    sys.exit(FAILURE_CONSTANT)
  try:
    dns_obj = DNS.DnsRequest(server=dns_server, timeout=timeout_in_sec)
  except Exception, error:
    logger.critical('failed to talk to DNS NS')
    logger.critical(e)
    sys.exit(FAILURE_CONSTANT)
  try:
    dns_response = dns_obj.req(reversed_ip + '.in-addr.arpa', qtype='PTR')
    if len(dns_response.answers):
      dns_answered = True
  except Exception as e:
    logger.info('failed to rev lookup target IP')
    logger.info(e)
    pass
  if dns_answered:
    return dns_response.answers[0]['data'].split('.')[0]
  else:
    return ip

def strip_port(ip_and_port, logger):
  '''strips :1234 from 10.10.10.10:1234'''
  try:
    ip, port = ip_and_port.split(':')
  except Exception as e:
    logger.critical('could not strip port from %s' % ip_and_port)
    logger.critical(e)
  return ip

def graphite_printer(all_stats, date, scheme, host_format=False):
  '''Takes a dict with stats_compute func structure flattens it for Graphite
  plain text protocol'''

  for host in all_stats:
    if host_format:
      host_formated = host.replace('.', '_')
      host_formated = host_formated.replace(':', '_')
    else:
      host_formated = host
    for bucket in all_stats[host]:
      for stat_name in all_stats[host][bucket]:
        for stats in all_stats[host][bucket][stat_name]:
          value = all_stats[host][bucket][stat_name][stats]
          if host_formated == 'per_bucket':
            print "%s.%s.%s.%s.%s %s %d" % (scheme, host_formated, bucket,
                stat_name, stats, value, date)
          else:
            print "%s.per_bucket_per_node.%s.%s.%s.%s %s %d" % (scheme, host_formated, bucket,
                stat_name, stats, value, date)

# Couchbase API dedicated functions
def get_buckets(couchbase_host, couchbase_rest_port, user, password, logger):
  '''Get CouchBase buckets from REST API'''
  try:
    query = 'http://%s:%s/pools/default/buckets' % (couchbase_host,
        couchbase_rest_port)
    response = requests.get(query, auth=(user, password))
    data = response.json()
  except Exception as e:
    logger.critical('Could not get buckets from Couchbase REST API')
    logger.critical(e)
    sys.exit(FAILURE_CONSTANT)
  buckets = []
  for bucket in data:
    buckets.append(bucket['name'])
  return buckets

def get_nodes_in_cluster(couchbase_host, couchbase_rest_port, user, password,
    logger):
  '''Get Couchbase cluster hostnames from REST API'''
  try:
    query = 'http://%s:%s/pools/default' % (couchbase_host, couchbase_rest_port)
    response = requests.get(query, auth=(user, password))
    data = response.json()
  except Exception as e:
    logger.critical('Could not get nodes from Couchbase REST API')
    logger.critical(e)
    sys.exit(FAILURE_CONSTANT)
  cb_nodes = []
  for node in data['nodes']:
    if node['clusterMembership'] == 'active':
      cb_nodes.append(node['hostname'])
  return cb_nodes

def urls_generator(couchbase_host, couchbase_rest_port, buckets,
    couchbase_nodes, logger, bucket_format=False):
  # This hits the same host to get all the stats but it can be changed to
  # hit each Couchbase node host for the per node stats
  '''Generate URLs from buckets and nodes to hit Couchbase REST API

   returns dict with following data structure:

   {'per_bucket_cluster_urls':[ ('per_bucket',<bucket_foo>,<URL_foo>),
                                    ('per_bucket',<bucket_bar>,<URL_bar>),...],

    'per_bucket_per_nodes_urls':[ (<node_foo>,<bucket_foo>,<URL_foo>),
                                  (<node_foo>,<bucket_bar>,<URL_bar>),
                                  (<node_baz>,<bucket_foo>,<URL_baz>),...]
   }'''

  cluster_nodes_buckets_urls = {}
  cluster_stats_urls = []
  per_node_urls = []
  for bucket in buckets:
    try:
      cluster_url = "http://%s:%s/pools/default/buckets/%s/stats" % (
          couchbase_host, couchbase_rest_port, bucket)
      if bucket_format:
        bucket_formated = bucket.replace('.', '_')
      else:
        bucket_formated = bucket
      cluster_bucket_url = ('per_bucket', bucket_formated, cluster_url)
      cluster_stats_urls.append(cluster_bucket_url)
    except Exception as e:
      logger.critical('Failed to generate list of URLs for per cluster queries')
      logger.critical(e)
      sys.exit(FAILURE_CONSTANT)
    try:
      for couchbase_node in couchbase_nodes:
        node_url = "http://%s:%s/pools/default/buckets/%s/nodes/%s/stats" % (
            couchbase_host, couchbase_rest_port, bucket, couchbase_node)
        if bucket_format:
          bucket_formated = bucket.replace('.', '_')
        else:
          bucket_formated = bucket
        node_bucket_url = (couchbase_node, bucket_formated, node_url)
        per_node_urls.append(node_bucket_url)
    except Exception as e:
      logger.critical('Failed to generate list of urls for per node queries')
      logger.critical(e)

  cluster_nodes_buckets_urls['per_bucket_cluster_urls'] = cluster_stats_urls
  cluster_nodes_buckets_urls['per_bucket_per_nodes_urls'] = per_node_urls
  return cluster_nodes_buckets_urls

def get_stats(url, user, password, cutoff, logger):
  '''Get couchbase stats (JSON) via REST API'''
  try:
    params = { 'haveTStamp': cutoff, 'zoom':'minute'}
    response = requests.get(url, auth=(user, password), params=params)
    return response.json()
  except Exception as e:
    logger.critical('Could not retrieve json data from %s' % url)
    logger.critical(e)
    sys.exit(FAILURE_CONSTANT)

def stats_compute(hosts_buckets_urls, stats_names, write_stats, user,
    password, cutoff, logger):
  hosts_buckets_stats = {}
  hosts_buckets_write_stats = {}
  for host_bucket_url in hosts_buckets_urls:
    host = host_bucket_url[0]
    bucket = host_bucket_url[1]
    url = host_bucket_url[2]
    stats = get_stats(url, user, password, cutoff, logger)
    stats_names_values = {}
    bucket_stats_names_values = {}
    # Needed because of len(stats) inconsistency in between queries
    number_of_data_points = len(stats['op']['samples'][write_stats[0]])

    # Calculate regular stats
    if host not in hosts_buckets_stats:
      hosts_buckets_stats[host] = {}

    for stat_name in stats_names:
      stats_names_values[stat_name] = min_med_max_avg(
          stats['op']['samples'][stat_name])
      bucket_stats_names_values[bucket] = stats_names_values
      host_buckets_stats_names_values = hosts_buckets_stats[host].copy()
      host_buckets_stats_names_values.update(bucket_stats_names_values)

    hosts_buckets_stats[host] = host_buckets_stats_names_values

    # Calculate write sums per bucket basis (per index)
    if host not in hosts_buckets_write_stats:
      hosts_buckets_write_stats[host] = {}

    if bucket not in hosts_buckets_write_stats[host]:
      hosts_buckets_write_stats[host][bucket] = {}
    # During testing got both 59 and 60 length depending on the buckets
    # (consistent per query) so we initialize the write sum list length
    # to the right value on a per bucket basis
      hosts_buckets_write_stats[host][bucket]['writes'] = [ 0 for x in range(0,
        number_of_data_points) ]

    for write_stat_name in write_stats:
      hosts_buckets_write_stats[host][bucket]['writes'] = map(add, stats[
        'op']['samples'][write_stat_name], hosts_buckets_write_stats[host][
          bucket]['writes'])

    hosts_buckets_write_stats[host][bucket]['writes'] = min_med_max_avg(
        hosts_buckets_write_stats[host][bucket]['writes'])

  # Merge the write stats to the regular stats
  for host in hosts_buckets_write_stats:
    for bucket in hosts_buckets_write_stats[host]:
      hosts_buckets_stats[host][bucket]['writes'] = hosts_buckets_write_stats[
          host][bucket]['writes']
  return hosts_buckets_stats

def main():
  parser = optparse.OptionParser()

  parser.add_option('-c', '--couchbase-host',
    help     = 'Couchbase metrics source host',
    dest     = 'couchbase_host',
    metavar  = 'COUCHBASE_HOST',
    type     = str)

  parser.add_option('-b', '--bucket_format',
    help     = 'replaces dots (.) in buckets names with underscores (_)',
    action   = 'store_true',
    default  = False,
    dest     = 'bucket_format')

  parser.add_option('-d', '--dns-lookup',
    help     = 'Try a rev DNS lookup for couchbase nodes host',
    action   = 'store_true',
    default  = False,
    dest     = 'rev_dns')

  parser.add_option('-i', '--interval',
    help     = 'Interval for stat collection in seconds, default to 60',
    dest     = 'interval',
    default  = 60,
    metavar  = 'INTERVAL',
    type     = int)

  parser.add_option('-r', '--host_format',
    help     = 'replaces dots (.) in nodes hostnames with underscores (_)',
    action   = 'store_true',
    default  = False,
    dest     = 'host_format')

  parser.add_option('-n', '--dns-name-server',
    help     = 'dns server for rev lookups',
    dest     = 'dns_ns',
    default  = '8.8.8.8',
    metavar  = 'DNS_NAMESERVER',
    type     = str)

  parser.add_option('-s', '--scheme',
    help    = 'Metric Graphite naming scheme, text to prepend to metric',
    default = 'couchbase',
    dest    = 'graphite_scheme',
    metavar = 'SCHEME')

  parser.add_option('-u', '--user',
    help     = 'couchbase user with access to rest',
    dest     = 'user',
    metavar  = 'USER')

  parser.add_option('-p', '--password',
    help     = 'couchbase user password',
    dest     = 'password',
    metavar  = 'PASSWORD')

  parser.add_option('-w', '--couchbase_rest_port',
    help     = 'couchbase REST port, defaults to 8091',
    default  = 8091,
    dest     = 'couchbase_rest_port',
    metavar  = 'COUCHBASE_REST_PORT')

  (options, args) = parser.parse_args()

  if not options.couchbase_host:
    print 'A couchbase metrics source host is required'
    sys.exit(FAILURE_CONSTANT)

  if not options.user or not options.password:
    print 'A couchbase user and password are required'
    sys.exit(FAILURE_CONSTANT)

  couchbase_host = options.couchbase_host
  couchbase_rest_port = options.couchbase_rest_port
  dns_ns = options.dns_ns
  interval = options.interval
  password = options.password
  graphite_scheme = options.graphite_scheme
  user = options.user

  logger = set_syslog()

  cutoff = int(time.time() - interval)

  # Generate URLs to hit for all buckets and all nodes
  buckets = get_buckets(couchbase_host, couchbase_rest_port, user, password,
      logger)
  cb_nodes = get_nodes_in_cluster(couchbase_host, couchbase_rest_port, user,
      password, logger)
  buckets_nodes_and_cluster_urls = urls_generator(couchbase_host,
      couchbase_rest_port, buckets, cb_nodes, logger,
      bucket_format=options.bucket_format)
  # Get and compute the stats

  ## Cluster stats
  cluster_buckets_urls = buckets_nodes_and_cluster_urls[
      'per_bucket_cluster_urls']
  cluster_stats = stats_compute(cluster_buckets_urls, PER_BUCKET_STATS,
      WRITE_STATS, user, password, cutoff, logger)

  ## Per node stats
  nodes_buckets_urls = buckets_nodes_and_cluster_urls[
      'per_bucket_per_nodes_urls']
  node_stats = stats_compute(nodes_buckets_urls, PER_BUCKET_PER_NODE_STATS,
      WRITE_STATS, user, password, cutoff, logger)
  ### Replace nodes IPs with hostnames via DNS rev lookup
  if options.rev_dns:
    node_stats_hostnames = {}
    for host in node_stats:
      ip = strip_port(host,logger)
      hostname = dns_reverse_lookup(dns_ns, 5, ip, logger)
      node_stats_hostnames[hostname] = node_stats[host]
    node_stats = node_stats_hostnames

  all_stats = cluster_stats.copy()
  all_stats.update(node_stats)

  now = time.time()
  graphite_printer(all_stats, now, options.graphite_scheme,
      host_format=options.host_format)

if __name__ == '__main__':
  main()
