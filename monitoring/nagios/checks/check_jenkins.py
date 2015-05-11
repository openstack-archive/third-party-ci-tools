#!/usr/bin/env python

import argparse
import urllib

import utils


def check_jenkins_status(job_name, warning_threshold, critial_threshold):
    """Returns a tuple of exit code and message string

    Exit codes are either 2 -> critical, 1 -> warning, or 0 -> OK
    There code is determined based on the job health score and thresholds
    passed into the script.
    """
    try:
        target_url = 'http://localhost:8080/job/%s/api/python' % job_name
        jenkins_volume_job = eval(urllib.urlopen(target_url).read())

        if jenkins_volume_job:
            health_score = jenkins_volume_job['healthReport'][0]['score']
            exit_code = 0
            if health_score <= critial_threshold:
                exit_code = 2
            elif health_score <= warning_threshold:
                exit_code = 1
            return exit_code, 'Jenkins job health score is ' + str(health_score)

    except Exception, e:
        return 2, 'Error checking jenkins job status: ' + e.message

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check jenkins job status.')
    parser.add_argument('--job', required=True, type=str, help='the job name to check for')
    parser.add_argument('-w', required=True, type=int, help='warning threshold of health score')
    parser.add_argument('-c', required=True, type=int, help='critical threshold of health score')
    args = parser.parse_args()
    code, message = check_jenkins_status(args.job, args.w, args.c)
    print message
    exit(code)