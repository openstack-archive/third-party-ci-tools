#!/bin/bash

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

# This script is to restrict which commands the FC passthrough is allowed
# to run using its key.
# To use it, copy it to /usr/local/bin/fc_commands.sh
# Then update the user's .ssh/authorize key file with the following line:
# command="/usr/local/bin/fc_commands.sh",no-agent-forwarding,no-port-forwarding,no-pty,no-user-rc,no-X11-forwarding ssh-rsa <fc-passthrough-public-key> fc-passthrough
#
# If you override the default values for some parameters in the
# invoke_fc_passthrough.sh script, you will need to update the
# list of ALLOWED_CMDS. For example: PROVIDER_RC & FC_PCI_VAR_NAME.
# This script assumes the default values.

SSH_ORIGINAL_COMMAND=${SSH_ORIGINAL_COMMAND:-$1}
IFS=$'\n'
ALLOWED_CMDS="
^source keystonerc_jenkins \&\& nova list$
^source keystonerc_jenkins \&\& nova show [a-f0-9]+-[a-f0-9]+-[a-f0-9]+-[a-f0-9]+-[a-f0-9]+$
^virsh nodedev-dettach pci_0000_[02][51]_00_[23]$
^scp -t /tmp/$
^virsh attach-device instance-[0-9a-f]* /tmp/tmp.*_fcoe.xml$
^echo \\\$fc_pci_device$"

#Don't allow any sudo commands
if [[ ! $SSH_ORIGINAL_COMMAND =~ sudo ]]; then
   for CMD in $ALLOWED_CMDS
   do
       if [[ $SSH_ORIGINAL_COMMAND =~ $CMD ]]; then
           eval $SSH_ORIGINAL_COMMAND
           # exit with the invoked command's return code for benefit of the caller
           exit $?
       fi
   done
fi
