define ciwatch::venv_wrapper(
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
  1> /var/log/ciwatch/${logbase}.log \
  2> /var/log/ciwatch/${logbase}_err.log
    ",
  }

}

