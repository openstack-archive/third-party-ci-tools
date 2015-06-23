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

# Run this as root on the OpenStack provider to setup the fc_pci_device
# environment variable needed for FC CI testing.
#
# If needed it will add an entry to /etc/profile.d/ with the variable.

if [[ -z $fc_pci_device ]]; then
    # Get all 'online' fc_host
    # Don't override any pre-set values because the device may not be "Online"
    # on subsequent runs
    HOST=$(sudo systool -c fc_host -A port_state | grep -B1 -m 1 "Online")
    if [[ -z $HOST ]]; then
      echo "Error, unable to find a FC Host that is 'Online'. You can add the 'fc_pci_device' variable manually to vars.sh"
    else
      fc_pci_device=$(systool -c fc_host -v | grep -B12 "Online" | grep "Class Device path" | cut -d / -f 6 | tr '\n' ' ')
      echo "Auto-detected FC PCI DEVICE: $fc_pci_device"
    fi
    echo "export fc_pci_device='$fc_pci_device'" >> /etc/profile.d/fc_devices.sh
fi
