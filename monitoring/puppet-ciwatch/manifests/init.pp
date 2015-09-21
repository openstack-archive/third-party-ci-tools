# Copyright (c) 2015 IBM Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# == Class: ciwatch
#
# Deploy Third-Party CI Watch.
#
# The dashboard consists of two services: gerrit listener and ui. The puppet
# module would not start these automatically and it is expected other means
# to be used.
# To manually start both: TODO:
#
# Dashboard's UI would be accessible on port 5000 (flask's default).
#
# === Parameters
#
# [*gerrit_user*]
#   Gerrit user account to be used by gerrit listener.
#
# [*ssh_private_key*]
#   Contents of ssh private key. This key needs to be authorized to connect
#   to gerrit account.

# [*gerrit_hostname*]
#   Gerrit server to be used for ciwatch gerrit listener.
#
# [*gerrit_port*]
#
#
# === Examples
#
# class { '::ciwatch':
#   gerrit_user     => hiera('ciwatch::gerit_user', 'XXX'),
#   ssh_private_key => hiera('ciwatch::ssh_private_key', 'XXX'),
# }
#
# === Authors
#
# Mikhail S Medvedev <mmedvede@us.ibm.com>
#
class ciwatch (
  $gerrit_user,
  $ssh_private_key,
  $gerrit_hostname = 'review.openstack.org',
  $gerrit_port = 29418,
) {

  $ssh_private_key_file = '/var/lib/ciwatch/ssh/id_rsa'
  # TODO: Figure out how CI Watch handles logging
  # $log_file_location = '/var/log/ciwatch/ciwatch.log'

  user { 'ciwatch':
    ensure     => present,
    home       => '/home/ciwatch',
    shell      => '/bin/bash',
    gid        => 'ciwatch',
    managehome => true,
    require    => Group['ciwatch'],
  }
  group { 'ciwatch':
    ensure => present,
  }

  # TODO: Add mysql database install/setup

  vcsrepo { '/opt/third-party-ci-tools':
    ensure   => latest,
    provider => git,
    revision => 'master',
    source   => 'http://github.com/stackforge/third-party-ci-tools',
  } ->
  file { '/opt/ciwatch':
    ensure => 'link',
    target => '/opt/third-party-ci-tools/monitoring/ciwatch',
  } ->
  python::virtualenv { '/usr/ciwatch-env':
    ensure       => present,
    requirements => '/opt/ciwatch/requirements.txt',
    owner        => 'root',
    group        => 'root',
    timeout      => 0,
  }

  file { '/etc/ciwatch/':
    ensure => directory,
  }
  # Template uses:
  # gerrit_user
  # ssh_private_key_file
  # gerrit_server
  # gerrit_port
  file { '/etc/ciwatch/ci-watch.conf':
    content => template('ciwatch/ci-watch.conf.erb'),
  }

  file { ['/var/lib/ciwatch', '/var/lib/ciwatch/ssh',]:
    ensure => directory,
  }
  file { $ssh_private_key_file:
    owner   => 'ciwatch',
    group   => 'ciwatch',
    mode    => '0400',
    content => $ssh_private_key,
  }

  file { '/var/log/ciwatch':
    ensure  => directory,
    owner   => 'ciwatch',
    recurse => true,  # Want to make sure all log permissions are set
    require => User['ciwatch'],
  }

  ::ciwatch::initd_service { 'ciwatch_ui':
    # TODO: need to find out what the actual command is
    # exec_cmd          => '/opt/ciwatch/ci-watch-server.py',
    venv_dir          => '/usr/ciwatch-env',
    short_description => 'CI Watch Web UI',
    runas_user        => 'ciwatch',
  }

  ::ciwatch::initd_service { 'ciwatch_gerrit_listener':
    # TODO: need to find out what the actual command is
    # exec_cmd          => '/opt/ciwatch/ci-watch-stream-events.py',
    venv_dir          => '/usr/ciwatch-env',
    short_description => 'CI Watch Gerrit Event Listener',
    runas_user        => 'ciwatch',
  }

}
