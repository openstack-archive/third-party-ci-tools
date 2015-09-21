define ciwatch::log_wrapper(
  $exec_cmd,
  $logbase,
  $wrapper_script = $title
) {

  file { $wrapper_script:
    mode    => '0555',
    content => "#!/usr/bin/env bash
${exec_cmd} \
  1> /var/log/ciwatch/${logbase}.log \
  2> /var/log/ciwatch/${logbase}_err.log
    ",
  }

}

