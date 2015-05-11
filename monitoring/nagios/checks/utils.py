import subprocess


def run_command_local(command):
    try:
        return subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
    except Exception, e:
        return e.message