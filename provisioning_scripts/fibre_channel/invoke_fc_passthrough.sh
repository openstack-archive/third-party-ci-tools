#!/usr/bin/env bash

# Copyright (C) 2015 Hewlett-Packard Development Company, L.P.
# Copyright (C) 2015 Pure Storage, Inc.
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


# Shell commands to get virsh the information it
# needs to successfully pass through a Fibre Channel PCI Card to the virtual
# machine this script is running on. The instance only knows its IP address,
# while its Virsh name is required for pass through. This script uses Nova on
# the provider blade as an intermediary to find the name. Meanwhile, this
# script finds the Fibre Channel PCI card on the provider and generates the
# information Virsh needs to attach it.
#
# Expect four env variables, the provider hostname (optionally user if needed)
# the private key file we should use to connect to the provider, and the file
# that should be sourced for OpenStack credentials.
#
# export FC_PROVIDER=my.provider.hostname
# export FC_PROVIDER_USER=root
# export FC_PROVIDER_KEY=/opt/nodepool-scripts/passthrough
# export FC_PROVIDER_RC=/root/keystonerc_jenkins
#
# The maximum number of FC devices to passthrough, failing if they cannot all be
# aquired
# export FC_NUM=2 (default 1)
#
# For single node setups where the hypervisor is the same as the provider, and dns
# is not configured, export this variable to use the provider ip as the hypervisor
# export FC_SINGLE_NODE=1

FC_NUM=${FC_NUM:-1}
FC_PCI_VAR_NAME=${FC_PCI_VAR_NAME:-"fc_pci_device"}

# Time in seconds to wait between dettach and attach for FC PCI devices.
# Some systems may need a few seconds, others 0 is fine.
FC_DETACH_WAIT_TIME=${FC_DETACH_WAIT_TIME:-0}

# Number of times to retry the passthrough to get the number of desired devices
FC_RETRY_COUNT=${FC_RETRY_COUNT:-3}

# Time in seconds to wait between retry attempts
FC_RETRY_SLEEP_TIME=${FC_RETRY_SLEEP_TIME:-0}

echo "Planning to passthrough $FC_NUM pci devices"

eth0_ip=$(hostname  -I | cut -f1 -d' ')

PROVIDER=${FC_PROVIDER}
if [[ -z $PROVIDER ]]; then
    eth0_ip_base=$(echo $eth0_ip | cut -f1,2,3 -d.)
    PROVIDER="${eth0_ip_base}.1"
fi

PROVIDER_KEY=${FC_PROVIDER_KEY:-"/opt-nodepool-scripts/passthrough"}
PROVIDER_RC=${FC_PROVIDER_RC:-"keystonerc_jenkins"}

CURRENT_USER=$(whoami)
PROVIDER_USER=${FC_PROVIDER_USER:-$CURRENT_USER}

# Passthrough is a private key that needs to be setup for the provider
# and any compute nodes that might end up hosting the VM we want passthrough on.
# We will assume ownership of the key (probably as the jenkins user..), also
# assuming the group is the same name as the user...
sudo chown $CURRENT_USER:$CURRENT_USER $PROVIDER_KEY
chmod 0400 $PROVIDER_KEY

# Get our NOVA_ID
NOVA_LIST=$(ssh -i $PROVIDER_KEY $PROVIDER_USER@$PROVIDER "source $PROVIDER_RC && nova list")
nova_result=$?
NOVA_ID=$(echo "$NOVA_LIST" | grep ACTIVE | grep -v deleting | grep $eth0_ip | cut -d \| -f 2 | tr -d '[:space:]')
echo "NOVA_ID result: $nova_result"
if [[ $nova_result -ne 0 || -z "$NOVA_ID" ]]; then
    echo "Unable to get Nova ID. Aborting. Debug info:"
    echo $NOVA_LIST
    echo "NOVA_ID: $NOVA_ID"
    exit 2
fi
echo "Found nova instance id: $NOVA_ID"

# Get instance details
NOVA_DETAILS=$(ssh -i $PROVIDER_KEY $PROVIDER_USER@$PROVIDER "source $PROVIDER_RC && nova show $NOVA_ID")
nova_results=$?

# Get our Virsh name
VIRSH_NAME=$(echo "$NOVA_DETAILS" | grep instance_name | cut -d \| -f 3 | tr -d '[:space:]')
virsh_result=$?
echo "VIRSH_NAME result: $virsh_result"
if [[ $nova_result -ne 0 || $virsh_result -ne 0 || -z "$VIRSH_NAME" ]]; then
    echo "Unable to get Virsh Name. Aborting. Debug info:"
    echo "NOVA_LIST:"
    echo $NOVA_LIST
    echo "NOVA_DETAILS:"
    echo $NOVA_DETAILS
    echo "VIRSH_NAME: $VIRSH_NAME"
    exit 2
fi
echo "Found virsh name: $VIRSH_NAME"

# Get the hypervisor_hostname
if [[ -z $FC_SINGLE_NODE ]]; then
    HYPERVISOR=$(echo "$NOVA_DETAILS" | grep hypervisor_hostname | cut -d \| -f 3 | tr -d '[:space:]')
    hypervisor_result=$?
    echo "HYPERVISOR result: $hypervisor_result"
    if [[ $hypervisor_result -ne 0 || -z "$HYPERVISOR" ]]; then
        echo "Unable to get Hypervisor Host Name. Aborting. Debug info:"
        echo "NOVA_LIST:"
        echo $NOVA_LIST
        echo "NOVA_DETAILS:"
        echo $NOVA_DETAILS
        echo "HYPERVISOR: $HYPERVISOR"
        exit 2
    fi
else
    HYPERVISOR=$PROVIDER
fi
echo "Found Hypervisor hostname: $HYPERVISOR"

fc_pci_device_cmd="echo \$$FC_PCI_VAR_NAME"
fc_pci_device=$(ssh -i $PROVIDER_KEY $PROVIDER_USER@$HYPERVISOR "$fc_pci_device_cmd")

if [[ -z $fc_pci_device ]]; then
    echo "No FC device known. Set fc_pci_device in your /etc/profile.d or /etc/environment (depending on distro and ssh configuration) to the desired 'Class Device path', e.g. '0000:21:00.2'"
    exit 2
fi

echo "Found potential PCI devices: $fc_pci_device"
echo "Atempting passthrough..."
exit_code=1
errexit=$(set +o | grep errexit)
#Ignore errors
set +e
let num_attached=0
let retry_count=0
while true; do
    for pci in $fc_pci_device; do
        echo "Trying FC PCI device: $pci"

        # Generate xml for virsh to use
        BUS=$(echo $pci | cut -d : -f2)
        SLOT=$(echo $pci | cut -d : -f3 | cut -d . -f1)
        FUNCTION=$(echo $pci | cut -d : -f3 | cut -d . -f2)
        XML="<hostdev mode='subsystem' type='pci' managed='yes'><source><address domain='0x0000' bus='0x$BUS' slot='0x$SLOT' function='0x$FUNCTION'/></source></hostdev>"
        echo "Virsh device xml: $XML"
        fcoe=`mktemp --suffix=_fcoe.xml`

        # Copy the tmp xml to the hypervisor
        echo $XML > $fcoe
        echo "Storing in $fcoe"
        echo "Copying..."
        scp -i $PROVIDER_KEY $fcoe $PROVIDER_USER@$HYPERVISOR:/tmp/

        # Detach the pci device so it can be passed through to a vm
        VIRSH_DEVICE="pci_0000_${BUS}_${SLOT}_${FUNCTION}"
        echo "Detaching $VIRSH_DEVICE..."
        ssh -i $PROVIDER_KEY $PROVIDER_USER@$HYPERVISOR "virsh nodedev-dettach $VIRSH_DEVICE"

        detach_result=$?
        echo "Detach result: $detach_result"
        if [[ $detach_result -ne 0 ]]; then
            echo "Detach failed. Trying next device..."
            continue
        fi

        sleep $FC_DETACH_WAIT_TIME

        echo "Attaching. $VIRSH_DEVICE..."
        ssh -i $PROVIDER_KEY $PROVIDER_USER@$HYPERVISOR "virsh attach-device $VIRSH_NAME $fcoe"
        attach_result=$?
        echo "Attach result: $attach_result"
        if [[ $attach_result -eq 0 ]]; then
            echo "Attached succeed. Trying next device..."
            (( num_attached += 1 ))
        fi
        echo "FC Devices after attach attempt:"
        echo $(sudo lspci | grep -i fib)
        echo "Total attached FC devices: $num_attached"
        if [[ $num_attached -eq $FC_NUM ]]; then
            echo "Attached $num_attached devices. Stopping"
            break
        fi
    done

    echo "Total attached FC devices: $num_attached"
    if [[ $num_attached -eq $FC_NUM ]]; then
        break
    fi

    if [[ retry_count -ge $FC_RETRY_COUNT ]]; then
        echo "FC requested $FC_NUM, but only attached $num_attached. Aborting after $retry_count attempts."
        exit 1
    fi
    (( retry_count += 1 ))
    echo "FC requested $FC_NUM, but only attached $num_attached. Retrying ($retry_count)..."
    sleep $FC_RETRY_SLEEP_TIME
done
$errexit

# Make sure that really it worked...
echo "Testing to ensure FC passthrough actuall worked..."
sudo modprobe lpfc || echo "Failed to find lpfc module!"

sudo systool -c fc_host -v || echo "Failed to find fc_host entries!"

echo "Final list of FC devices:"
echo $(sudo lspci | grep -i fib)

let retry_count=0
while true; do
    device_path=$(sudo systool -c fc_host -v | grep "Device path")
    if [[ ${#device_path}  -eq 0 ]]; then
        if [[ retry_count -ge $FC_RETRY_COUNT ]]; then
            echo "Failed to find FC Device path with $num_attached devices. Aborting after $retry_count attempts."
            exit 1
        fi
        (( retry_count += 1 ))
        echo "Unable to verify FC hosts. Retrying ($retry_count)..."
        sleep $FC_RETRY_SLEEP_TIME
    else
        break
    fi
done

echo "FC Passthrough success!"