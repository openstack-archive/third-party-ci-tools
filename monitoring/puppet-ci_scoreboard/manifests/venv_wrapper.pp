define ci_scoreboard::venv_wrapper(
  $venv_dir,
  $exec_cmd,
  $logbase,
  $wrapper_script = $title
) {

  file { $wrapper_script:
    mode    => '0555',
    content => "#!/usr/bin/env bash
source ${venv_dir}/bin/activate
${exec_cmd} \
  1> /var/log/scoreboard/${logbase}.log \
  2> /var/log/scoreboard/${logbase}_err.log
    ",
  }

}

