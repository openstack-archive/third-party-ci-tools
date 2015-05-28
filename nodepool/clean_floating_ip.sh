#!/usr/bin/env bash

# Copyright (C) 2015 Hewlett-Packard Development Company, L.P.
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
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Nodepool tends to leak floating ip address. Workaround by adding this script to
# /etc/cron.hourly to periodically clean up leaked ip addresses.
#
# export RC=/root/keystonerc_jenkins
#

RC=${RC:-"/home/stack/devstack/accrc/admin/admin"}

source $RC
for ip in `nova floating-ip-list | grep public | grep "| -" | cut -d \| -f 2`; do
    echo "Deleting unused floating $ip"
    nova floating-ip-delete $ip
done
