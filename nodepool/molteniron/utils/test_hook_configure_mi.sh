#!/bin/bash

# Copyright (c) 2016 IBM Corporation.
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

errcho()
{
  # Redirect stdout to stderr for the echo command
  >&2 echo $@;
}

#
# NOTE:
#
# This script expects the environment variable dsvm_uuid to be set!
#

if [ -z "${dsvm_uuid}" ]
then
  errcho "Error: environment variable unset: dsvm_uuid"
  exit 1
fi

# Is the command-line JSON processor installed?
hash jq || sudo apt-get install -y jq

# Turn off Bash debugging temporarily to stop password being shown in log files
set +x

# allocate a BM node to a dsvm guest named dsvm_uuid, then amend the localrc
# and hardware_info files.
JSON_RSP=$(molteniron allocate $dsvm_uuid 1)

if [ $? -gt 0 ]
then
  # Save the response for local debugging
  echo "${JSON_RSP}" > /tmp/json.rsp

  errcho "Error: allocate $dsvm_uuid 1"

  MESSAGE=$(echo "${JSON_RSP}" | jq .message)

  # Is there a message response?
  # NOTE: jq not finding a message key returns null
  if [ $? -eq 0 -a "${MESSAGE}" != "null" ]
  then
      errcho "Error: ${MESSAGE}"
  fi

  exit 1
fi

# Convert from a JSON string into a Bash array
declare -A NODE
while IFS="=" read -r key value
do
  NODE[$key]="$value"
done < <(
  echo ${JSON_RSP} | jq --raw-output '.nodes[]|to_entries|map("\(.key)=\(.value|tostring)")|.[]'
  RC=$?
  if [ ${RC} -gt 0 ]
  then
    echo "error=${RC}"
  fi
)

if [ -n "${NODE[error]}" ]
then
  errcho "Error: jq failed to parse response"
  errcho "jq .nodes:"
  errcho ${JSON_RSP} | jq '.nodes[]'
  errcho "jq .nodes|to_entries|map:"
  errcho ${JSON_RSP} | jq --raw-output '.nodes[]|to_entries|map("\(.key)=\(.value|tostring)")|.[]'
  exit 2
elif [  -z "${NODE[ipmi_ip]}" \
     -o -z "${NODE[port_hwaddr]}" \
     -o -z "${NODE[ipmi_user]}" \
     -o -z "${NODE[ipmi_password]}" ]
then
  echo "ERROR: One of NODE's ipmi_ip, port_hwaddr, ipmi_user, or ipmi_password is empty!"
  if [ -n "${NODE[ipmi_password]}" ]
  then
      SAFE_PASSWORD="*hidden*"
  else
      SAFE_PASSWORD=""
  fi
  echo "NODE[ipmi_ip]       = ${NODE[ipmi_ip]}"
  echo "NODE[port_hwaddr]   = ${NODE[port_hwaddr]}"
  echo "NODE[ipmi_user]     = ${NODE[ipmi_user]}"
  echo "NODE[ipmi_password] = ${SAFE_PASSWORD}"
  echo "jq command returns:"
  echo ${JSON_RSP} | jq --raw-output '.nodes[]|to_entries|map("\(.key)=\(.value|tostring)")|.[]'
  exit 3
fi

# Set IPMI info file
printf "${NODE[ipmi_ip]} ${NODE[port_hwaddr]} ${NODE[ipmi_user]} ${NODE[ipmi_password]}\\n" > "/opt/stack/new/devstack/files/hardware_info"

set -x

# Add the hardware properties to the localrc file
printf "IRONIC_HW_ARCH=${NODE[cpu_arch]}\\nIRONIC_HW_NODE_CPU=${NODE[cpus]}\\nIRONIC_HW_NODE_RAM=${NODE[ram_mb]}\\nIRONIC_HW_NODE_DISK=${NODE[disk_gb]}\\n" >> "/opt/stack/new/devstack/localrc"

# Add the allocation pools to the localrc
IFS=',' read -r -a ALLOCATION_POOL <<< ${NODE[allocation_pool]}

POOL=''
for IP in ${ALLOCATION_POOL[@]}
do
  echo "IP=${IP}"
  if [ -n "${POOL}" ]
  then
    POOL+=" --allocation-pool "
  fi
  POOL+="start=${IP},end=${IP}"
done
# append ip pools to the end of our localrc
printf "ALLOCATION_POOL=\"${POOL}\"\n" >>  "/opt/stack/new/devstack/localrc"
