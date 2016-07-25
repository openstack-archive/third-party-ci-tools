#!/bin/bash

# Copyright 2016 IBM Corp.
#
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
#
# This script manage binding\unbinding a pci device with vfio driver
# The script gets a string in form of Domain:Bus:Device.Function
# and perform requested operation according to the command line argument:
#
#    -h             Display help message and exit
#    -l             List devices binded to vfio-pci kernel driver
#    -r             Force a rescan of pci devices
#    -u PCI_DEVICE  Unbind vfio-pci and remove. PCI_DEVICE is Domain:Bus:Device string of the form "0000:00:00.0"
#    -b PCI_DEVICE  Bind vfio-pci. PCI_DEVICE is Domain:Bus:Device string of the form "0000:00:00.0"

function iommu_group_devs {
    INPUT_PCI_DEV=$1
    INPUT_PCI_DEV_SYSFS_PATH="/sys/bus/pci/devices/$INPUT_PCI_DEV"
    if [[ ! -d $INPUT_PCI_DEV_SYSFS_PATH ]]; then
        echo "There is no device: $INPUT_PCI_DEV" 1>&2
        exit 1
    fi

    if [[ ! -d "$INPUT_PCI_DEV_SYSFS_PATH/iommu/" ]]; then
        echo "Check IOMMU definition." 1>&2
        echo "Use intel_iommu=on or iommu=pt iommu=1" 1>&2
        exit 1
    fi

    for pcid in $INPUT_PCI_DEV_SYSFS_PATH/iommu_group/devices/*
    do
        dbdf=${pcid##*/}
        if [[ $(( 0x$(setpci -s $dbdf 0e.b) & 0x7f )) -eq 0 ]]; then
            dev_sysfs_paths+=( ${pcid##*/} )
        fi
    done
    echo "${dev_sysfs_paths[@]}"
}

function vfio_unbind {
    DEV=$1
    echo "Trying to unbind: $DEV"
    if [ -e /sys/bus/pci/drivers/vfio-pci/$DEV/remove ]; then
        echo "Removing device: $DEV" 1>&2
        echo 1 > /sys/bus/pci/drivers/vfio-pci/$DEV/remove
    else
        echo "Device: $DEV not found" 1>&2
        return 1
    fi
    return 0
}

function vfio_bind {
    DEV=$1
    echo "Trying to bind: $DEV"
    #/sys/bus/pci/devices/0000:20:00.0/iommu_group/devices/0000:20:00.0
    dpath="/sys/bus/pci/devices/$DEV"
    echo "vfio-pci" > "$dpath/driver_override"

    if [[ -d $dpath ]]; then
        curr_driver=$(readlink $dpath/driver)
        curr_driver=${curr_driver##*/}

        if [[ $curr_driver == "vfio-pci" ]]; then
            echo "$DEV already bound to vfio-pci" 1>&2
            continue
        else
            echo $DEV > "$dpath/driver/unbind"
            echo "Unbound $DEV from $curr_driver" 1>&2
        fi
    fi

    echo $DEV > /sys/bus/pci/drivers_probe
}

# Usage info
show_help() {
cat << EOF
Usage: ${0##*/} [-h] [-u PCI_DEVICE] PCI_DEVICE...
This script enble binding/unbinding pci devices to vfio-pci driver

    -h             Display this help and exit
    -l             List devices bind to vfio-pci kernel driver
    -r             Force a rescan of pci devices
    -u PCI_DEVICE  Unbind vfio-pci. PCI_DEVICE is Domain:Bus:Device string of the form "0000:00:00.0"
    -b PCI_DEVICE  Bind vfio-pci. PCI_DEVICE is Domain:Bus:Device string of the form "0000:00:00.0"
EOF
}


if [ "$#" -lt 1 ];then
  echo "illegal number of arguments: $#"
  show_help
  exit 1
fi

OPTIND=1
while getopts "hlru:b:" opt; do
    options_found=1
    case "$opt" in
        h)
            show_help
            exit 0
            ;;
        l)
            lspci -k | grep -i vfio-pci -B2 | grep -i fib | awk '{print $1}'
            exit 0
            ;;
        r)  echo "Run PCI rescan"
            echo 1 > /sys/bus/pci/rescan
            exit $?
            ;;
        u)  device=$OPTARG
            devs="$(iommu_group_devs $device)"
            if [[ -n $devs ]]; then
                for dpci in $devs
                do
                    echo "Remove device: $dpci"
                    vfio_unbind $dpci
                    if [[ $? -ne 0 ]]; then
                        echo "Unbind Devices error" 1>&2
                        exit 1
                    fi
                done
                exit 0
            fi
            exit 1
            ;;
        b)  device=$OPTARG
            modprobe -i vfio-pci
            if [[ $? -ne 0 ]]; then
                echo "Error probing vfio-pci" 1>&2
                exit 1
            fi
            devs="$(iommu_group_devs $device)"
            if [[ -n $devs ]]; then
                for dpci in $devs
                do
                    echo "Binding device: $dpci"
                    vfio_bind $dpci
                    if [[ $? -ne 0 ]]; then
                        echo "Device binding error: $dpci"
                        exit 1
                    fi
                done
                exit 0
            fi
            exit 1
            ;;
        \?)
            show_help >&2
            exit 1
            ;;
    esac
done
shift "$((OPTIND-1))" # Shift off the options and optional --.

if ((!options_found)); then
  echo "no options found"
  show_help
fi
