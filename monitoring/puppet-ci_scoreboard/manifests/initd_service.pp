# == Define: ci_scoreboard::initd_service
#
# Creates initd service for an executable which can not run as daemon and
# runs it in the python virtualenv.

define ci_scoreboard::initd_service(
  $exec_cmd,
  $venv_dir,
  $short_description,
  $runas_user,
  $service_name = $title,
) {

  ::ci_scoreboard::venv_wrapper{ "/usr/local/bin/${service_name}":
    venv_dir => $venv_dir,
    exec_cmd => $exec_cmd,
    logbase  => $service_name,
  }

  # Template uses:
  # service_name
  # short_description
  # runas_user
  file { "/etc/init.d/${service_name}":
    ensure  => present,
    owner   => 'root',
    group   => 'root',
    mode    => '0555',
    content => template('ci_scoreboard/scoreboard_service.init.erb'),
  }

  service { $service_name:
    enable     => true,
    hasrestart => true,
    require    => File["/etc/init.d/${service_name}"],
  }

}
