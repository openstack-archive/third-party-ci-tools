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

# == Class: ci_scoreboard
#
# Deploy Third-Party CI Scoreboard.
#
# Scoreboard consists of two services: gerrit listener and ui. The puppet
# module would not start these automatically and it is expected other means
# to be used.
# To manually start both:
#   service scoreboard_ui start
#   service scoreboard_gerrit_listener start
#
# Scoreboard's UI would be accessible on port 5000 (flask's default).
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
#   Gerrit server to be used for scoreboard gerrit listener.
#
# [*gerrit_port*]
#
# [*gerrit_keepalive*]
#   Keepalive interval in seconds, or disabled when 0 (default)
#
#
# === Examples
#
# class { '::ci_scoreboard':
#   gerrit_user     => hiera('ci_scoreboard::gerit_user', 'XXX'),
#   ssh_private_key => hiera('ci_scoreboard::ssh_private_key', 'XXX'),
# }
#
# === Authors
#
# Mikhail S Medvedev <mmedvede@us.ibm.com>
#
class ci_scoreboard (
  $gerrit_user,
  $ssh_private_key,
  $gerrit_hostname = 'review.openstack.org',
  $gerrit_port = 29418,
  $gerrit_keepalive = 0,
) {

  $ssh_private_key_file = '/var/lib/scoreboard/ssh/id_rsa'
  $log_file_location = '/var/log/scoreboard/scoreboard.log'

  user { 'scoreboard':
    ensure     => present,
    home       => '/home/scoreboard',
    shell      => '/bin/bash',
    gid        => 'scoreboard',
    managehome => true,
    require    => Group['scoreboard'],
  }
  group { 'scoreboard':
    ensure => present,
  }

  package{ 'mongodb':
    ensure => present;
  } ->
  service{ 'mongodb':
    ensure => running,
    enable => true,
  }

  vcsrepo { '/opt/third-party-ci-tools':
    ensure   => latest,
    provider => git,
    revision => 'master',
    source   => 'http://github.com/openstack/third-party-ci-tools',
  } ->
  file { '/opt/scoreboard':
    ensure => 'link',
    target => '/opt/third-party-ci-tools/monitoring/scoreboard',
  } ->
  python::virtualenv { '/usr/scoreboard-env':
    ensure       => present,
    requirements => '/opt/scoreboard/requirements.txt',
    owner        => 'root',
    group        => 'root',
    timeout      => 0,
  }

  file { '/etc/ci-scoreboard/':
    ensure => directory,
  }
  # Template uses:
  # gerrit_user
  # ssh_private_key_file
  # gerrit_server
  # gerrit_port
  # log_file_location
  file { '/etc/ci-scoreboard/ci-scoreboard.conf':
    content => template('ci_scoreboard/ci-scoreboard.conf.erb'),
  }

  file { ['/var/lib/scoreboard', '/var/lib/scoreboard/ssh',]:
    ensure => directory,
  }
  file { $ssh_private_key_file:
    owner   => 'scoreboard',
    group   => 'scoreboard',
    mode    => '0400',
    content => $ssh_private_key,
  }

  file { '/var/log/scoreboard':
    ensure  => directory,
    owner   => 'scoreboard',
    recurse => true,  # Want to make sure all log permissions are set
    require => User['scoreboard'],
  }

  ::ci_scoreboard::initd_service { 'scoreboard_ui':
    exec_cmd          => '/opt/scoreboard/scoreboard_ui.py',
    venv_dir          => '/usr/scoreboard-env',
    short_description => 'CI Scoreboard Web UI',
    runas_user        => 'scoreboard',
  }

  ::ci_scoreboard::initd_service { 'scoreboard_gerrit_listener':
    exec_cmd          => '/opt/scoreboard/scoreboard_gerrit_listener.py',
    venv_dir          => '/usr/scoreboard-env',
    short_description => 'CI Scoreboard Gerrit Event Listener',
    runas_user        => 'scoreboard',
  }

}
