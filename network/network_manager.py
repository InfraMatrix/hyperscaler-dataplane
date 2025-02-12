#!/usr/bin/env python3

# Copyright © 2025 InfraMatrix. All Rights Reserved.

# SPDX-License-Identifier: BSD-3-Clause

from pyroute2 import IPRoute
import subprocess
import sys
import random
import yaml

from network.ip_manager import IPManager

def run_network_cmd(cmd):
    try:
        result = subprocess.run(cmd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False)
    except subprocess.CalledProcessError as e:
        if e.returncode != 2 and "already exists" not in str(e.stderr):
            print(f"Command: {cmd} failed: {e}")
            return False
    return True

class NetworkManager:

    def __init__(self):
        self._host_network_interface = IPRoute()
        self._used_macs = []
        self.vm_ssh_ports = list(range(7600,7700))
        self.port_map = {}
        self.ip_manager = IPManager("192.168.100.1")

        add_bridge_cmd = ["ovs-vsctl", "add-br", "ovs-vm-bridge"]
        run_network_cmd(add_bridge_cmd)

        setup_bridge_cmd = ["ip", "link", "set", "ovs-vm-bridge", "up"]
        run_network_cmd(setup_bridge_cmd)

        add_bridge_ip_cmd = ["ip", "addr", "add", "192.168.100.1/24", "dev", "ovs-vm-bridge"]
        run_network_cmd(add_bridge_ip_cmd)

        iptables_commands = [
            ['sudo', 'iptables', '-t', 'nat', '-A', 'POSTROUTING', '-o', 'enp14s0', '-j', 'MASQUERADE'],
            ['sudo', 'iptables', '-A', 'FORWARD', '-i', 'ovs-vm-bridge', '-o', 'enp14s0', '-j', 'ACCEPT'],
            ['sudo', 'iptables', '-A', 'FORWARD', '-i', 'enp14s0', '-o', 'ovs-vm-bridge', '-m', 'state',
                '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT']
        ]
        for cmd in iptables_commands:
            run_network_cmd(cmd)

    def setup_vm_networking_interface(self, vm_name=""):
        tap_name = vm_name + "_tap"

        if (not self._host_network_interface.link_lookup(ifname=tap_name)):
            self._host_network_interface.link('add', ifname=tap_name, kind="tuntap", mode="tap")
            tap_index = self._host_network_interface.link_lookup(ifname=tap_name)[0]
            self._host_network_interface.link('set', index=tap_index, state='up')

        result = subprocess.run(['ovs-vsctl', 'add-port', "vm_switch", tap_name])

        return tap_name

    def generate_mac(self):
        mac = ""
        while (mac not in self._used_macs):
            mac = '02:%02x:%02x:%02x:%02x:%02x' % tuple(random.randint(0, 255) for _ in range(5))
            self._used_macs.append(mac)
            return mac

    def acquire_vm_port(self, vm_name):
        vm_port = self.vm_ssh_ports[0]
        self.port_map[vm_name] = vm_port
        self.vm_ssh_ports.pop(0)
        return vm_port

    def release_vm_port(self, vm_name):
        self.vm_ssh_ports.append(self.port_map(vm_name))
        self.port_map.remove(vm_name)

    def allocate_vm_tap_interface(self, vm_name):
        tap_name = f"tap_{vm_name}"[:15]

        create_tap_cmd = ["ip", "tuntap", "add", "dev", tap_name, "mode", "tap"]
        run_network_cmd(create_tap_cmd)

        add_tap_ovs_cmd = ["ovs-vsctl", "add-port", "ovs-vm-bridge", tap_name]
        run_network_cmd(add_tap_ovs_cmd)

        set_tap_up_cmd = ["ip", "link", "set", tap_name, "up"]
        run_network_cmd(set_tap_up_cmd)

        return tap_name

    def deallocate_vm_tap_interface(self, vm_name):
        tap_name = f"tap_{vm_name}"[:15]

        add_tap_ovs_cmd = ["ovs-vsctl", "del-port", "ovs-vm-bridge", tap_name]
        run_network_cmd(add_tap_ovs_cmd)

        create_tap_cmd = ["ip", "tuntap", "del", "dev", tap_name, "mode", "tap"]
        run_network_cmd(create_tap_cmd)

    def get_vm_mac(self, vm_name):
        try:
            with open(f"/IGS/compute/vms/{vm_name}/user-data", 'r') as f:
                config = yaml.safe_load(f)

            for wf in config.get('write_files', []):
                if wf.get('path') == "/etc/netplan/99-netcfg.yaml":
                    netplan_content = yaml.safe_load(wf['content'])
                    interfaces = netplan_content.get('network', {}).get('ethernets', {})
                    for interface in interfaces.values():
                        if 'match' in interface and 'macaddress' in interface['match']:
                            return interface['match']['macaddress']
        except Exception as e:
            return ""

    def get_vm_ip(self, vm_name):
        vm_ip = self.ip_manager.get_vm_ip(vm_name=vm_name)
        return vm_ip
