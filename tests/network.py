#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# The Qubes OS Project, http://www.qubes-os.org
#
# Copyright (C) 2015 Marek Marczykowski-Górecki <marmarek@invisiblethingslab.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.
#
import multiprocessing
import os
import subprocess
import unittest
import time

from qubes.qubes import QubesVmCollection, defaults


VM_PREFIX = "test-"

class VmNetworkingTests(unittest.TestCase):
    ping_ip =  "ping -W 1 -n -c 1 192.168.123.45"
    ping_name = "ping -W 1 -c 1 test.example.com"

    def run_cmd(self, vm, cmd, user="root"):
        p = vm.run(cmd, user=user, passio_popen=True, ignore_stderr=True)
        p.stdin.close()
        p.stdout.read()
        return p.wait()

    def setUp(self):
        self.qc = QubesVmCollection()
        self.qc.lock_db_for_writing()
        self.qc.load()
        self.testnetvm = self.qc.add_new_vm("QubesNetVm",
                                            name="%snetvm1" % VM_PREFIX,
                                            template=self.qc.get_default_template())
        self.testnetvm.create_on_disk(verbose=False)
        self.testvm1 = self.qc.add_new_vm("QubesAppVm",
                                          name="%svm2" % VM_PREFIX,
                                          template=self.qc.get_default_template())
        self.testvm1.create_on_disk(verbose=False)
        self.testvm1.netvm = self.testnetvm
        self.qc.save()
        self.qc.unlock_db()
        self.configure_netvm()

    def configure_netvm(self):
        def run_netvm_cmd(cmd):
            if self.run_cmd(self.testnetvm, cmd) != 0:
                self.fail("Command '%s' failed" % cmd)

        if not self.testnetvm.is_running():
            self.testnetvm.start()
        # Ensure that dnsmasq is installed:
        p = self.testnetvm.run("dnsmasq --version", user="root",
                               passio_popen=True)
        if p.wait() != 0:
            self.skipTest("dnsmasq not installed")

        run_netvm_cmd("ip link add test0 type dummy")
        run_netvm_cmd("ip link set test0 up")
        run_netvm_cmd("ip addr add 192.168.123.45/24 dev test0")
        run_netvm_cmd("iptables -I INPUT -d 192.168.123.45 -j ACCEPT")
        run_netvm_cmd("dnsmasq -a 192.168.123.45 -A /example.com/192.168.123.45 -i test0 -z")
        run_netvm_cmd("echo nameserver 192.168.123.45 > /etc/resolv.conf")
        run_netvm_cmd("/usr/lib/qubes/qubes-setup-dnat-to-ns")

    def remove_vms(self, vms):
        self.qc.lock_db_for_writing()
        self.qc.load()

        for vm in vms:
            if isinstance(vm, str):
                vm = self.qc.get_vm_by_name(vm)
            else:
                vm = self.qc[vm.qid]
            if vm.is_running():
                try:
                    vm.force_shutdown()
                except:
                    pass
            try:
                vm.remove_from_disk()
            except OSError:
                pass
            self.qc.pop(vm.qid)
        self.qc.save()
        self.qc.unlock_db()

    def tearDown(self):
        vmlist = [vm for vm in self.qc.values() if vm.name.startswith(
            VM_PREFIX)]
        self.remove_vms(vmlist)

    def test_000_simple_networking(self):
        self.testvm1.start()
        self.assertEqual(self.run_cmd(self.testvm1,
                                      "ping -c 1 192.168.123.45"), 0)
        self.assertEqual(self.run_cmd(self.testvm1,
                                      "ping -c 1 test.example.com"), 0)

    def test_010_simple_proxyvm(self):
        self.qc.lock_db_for_writing()
        self.qc.load()
        self.proxy = self.qc.add_new_vm("QubesProxyVm",
                                          name="%sproxy" % VM_PREFIX,
                                          template=self.qc.get_default_template())
        self.proxy.create_on_disk(verbose=False)
        self.proxy.netvm = self.testnetvm
        self.testvm1.netvm = self.proxy
        self.qc.save()
        self.qc.unlock_db()

        self.testvm1.start()
        self.assertTrue(self.proxy.is_running())
        self.assertEqual(self.run_cmd(self.proxy, self.ping_ip), 0,
                         "Ping by IP from ProxyVM failed")
        self.assertEqual(self.run_cmd(self.proxy, self.ping_name), 0,
                         "Ping by name from ProxyVM failed")
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_ip), 0,
                         "Ping by IP from AppVM failed")
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_name), 0,
                         "Ping by IP from AppVM failed")

    def test_020_simple_proxyvm_nm(self):
        self.qc.lock_db_for_writing()
        self.qc.load()
        self.proxy = self.qc.add_new_vm("QubesProxyVm",
                                          name="%sproxy" % VM_PREFIX,
                                          template=self.qc.get_default_template())
        self.proxy.create_on_disk(verbose=False)
        self.proxy.netvm = self.testnetvm
        self.proxy.services['network-manager'] = True
        self.testvm1.netvm = self.proxy
        self.qc.save()
        self.qc.unlock_db()

        self.testvm1.start()
        self.assertTrue(self.proxy.is_running())
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_ip), 0,
                         "Ping by IP failed")
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_name), 0,
                         "Ping by name failed")
        # reconnect to make sure that device was configured by NM
        self.assertEqual(
            self.run_cmd(self.proxy, "nmcli device disconnect eth0",
                         user="user"),
            0, "Failed to disconnect eth0 using nmcli")

        self.assertEqual(self.run_cmd(self.testvm1, self.ping_ip), 1,
                         "Network should be disabled, but apparently it isn't")
        self.assertEqual(
            self.run_cmd(self.proxy, "nmcli connection up \"VM uplink eth0\" "
                                     "ifname eth0",
                         user="user"),
            0, "Failed to connect eth0 using nmcli")
        self.assertEqual(self.run_cmd(self.proxy, "nm-online", user="user"), 0,
                         "Failed to wait for NM connection")
        # check for nm-applet presence
        self.assertEqual(subprocess.call([
            'xdotool', 'search', '--all', '--name',
            '--class', '^(NetworkManager Applet|{})$'.format(self.proxy.name)
        ], stdout=open('/dev/null', 'w')), 0, "nm-applet window not found")
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_ip), 0,
                         "Ping by IP failed (after NM reconnection")
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_name), 0,
                         "Ping by name failed (after NM reconnection)")

    def test_030_firewallvm_firewall(self):
        self.qc.lock_db_for_writing()
        self.qc.load()
        self.proxy = self.qc.add_new_vm("QubesProxyVm",
                                          name="%sproxy" % VM_PREFIX,
                                          template=self.qc.get_default_template())
        self.proxy.create_on_disk(verbose=False)
        self.proxy.netvm = self.testnetvm
        self.testvm1.netvm = self.proxy
        self.qc.save()
        self.qc.unlock_db()

        # block all for first

        self.testvm1.write_firewall_conf({
            'allow': False,
            'allowDns': False,
            'allowIcmp': False,
        })
        self.testvm1.start()
        self.assertTrue(self.proxy.is_running())

        self.testnetvm.run("nc -l --send-only -e /bin/hostname -k 1234")

        self.assertEqual(self.run_cmd(self.proxy, self.ping_ip), 0,
                         "Ping by IP from ProxyVM failed")
        self.assertEqual(self.run_cmd(self.proxy, self.ping_name), 0,
                         "Ping by name from ProxyVM failed")
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_ip), 1,
                         "Ping by IP should be blocked")
        nc_cmd = "nc -w 1 --recv-only 192.168.123.45 1234"
        self.assertEqual(self.run_cmd(self.testvm1, nc_cmd), 1,
                         "TCP connection should be blocked")

        # block all except ICMP

        self.testvm1.write_firewall_conf({
            'allow': False,
            'allowDns': False,
            'allowIcmp': True,
        })
        self.proxy.write_iptables_xenstore_entry()
        # Ugly hack b/c there is no feedback when the rules are actually applied
        time.sleep(1)
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_ip), 0,
                         "Ping by IP failed (should be allowed now)")
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_name), 2,
                         "Ping by name should be blocked")

        # all TCP still blocked

        self.testvm1.write_firewall_conf({
            'allow': False,
            'allowDns': True,
            'allowIcmp': True,
        })
        self.proxy.write_iptables_xenstore_entry()
        # Ugly hack b/c there is no feedback when the rules are actually applied
        time.sleep(1)
        self.assertEqual(self.run_cmd(self.testvm1, self.ping_name), 0,
                         "Ping by name failed (should be allowed now)")
        self.assertEqual(self.run_cmd(self.testvm1, nc_cmd), 1,
                         "TCP connection should be blocked")

        # block all except target

        self.testvm1.write_firewall_conf({
            'allow': False,
            'allowDns': True,
            'allowIcmp': True,
            'rules': [{'address': '192.168.123.45',
                       'netmask': 32,
                       'proto': 'tcp',
                       'portBegin': 1234
                      }] })
        self.proxy.write_iptables_xenstore_entry()
        # Ugly hack b/c there is no feedback when the rules are actually applied
        time.sleep(1)
        self.assertEqual(self.run_cmd(self.testvm1, nc_cmd), 0,
                         "TCP connection failed (should be allowed now)")

        # allow all except target

        self.testvm1.write_firewall_conf({
            'allow': True,
            'allowDns': True,
            'allowIcmp': True,
            'rules': [{'address': '192.168.123.45',
                       'netmask': 32,
                       'proto': 'tcp',
                       'portBegin': 1234
                      }]
        })
        self.proxy.write_iptables_xenstore_entry()
        # Ugly hack b/c there is no feedback when the rules are actually applied
        time.sleep(1)
        self.assertEqual(self.run_cmd(self.testvm1, nc_cmd), 1,
                         "TCP connection should be blocked")


    def test_040_inter_vm(self):
        self.qc.lock_db_for_writing()
        self.qc.load()
        self.proxy = self.qc.add_new_vm("QubesProxyVm",
                                          name="%sproxy" % VM_PREFIX,
                                          template=self.qc.get_default_template())
        self.proxy.create_on_disk(verbose=False)
        self.proxy.netvm = self.testnetvm
        self.testvm1.netvm = self.proxy

        self.testvm2 = self.qc.add_new_vm("QubesAppVm",
                                          name="%svm3" % VM_PREFIX,
                                          template=self.qc.get_default_template())
        self.testvm2.create_on_disk(verbose=False)
        self.testvm2.netvm = self.proxy
        self.qc.save()
        self.qc.unlock_db()

        self.testvm1.start()
        self.testvm2.start()

        self.assertEqual(self.run_cmd(self.testvm1,
                     "ping -W 1 -n -c 1 {}".format(self.testvm2.ip)), 1)

        self.testvm2.netvm = self.testnetvm

        self.assertEqual(self.run_cmd(self.testvm1,
             "ping -W 1 -n -c 1 {}".format(self.testvm2.ip)), 1)
        self.assertEqual(self.run_cmd(self.testvm2,
             "ping -W 1 -n -c 1 {}".format(self.testvm1.ip)), 1)

        self.testvm1.netvm = self.testnetvm

        self.assertEqual(self.run_cmd(self.testvm1,
             "ping -W 1 -n -c 1 {}".format(self.testvm2.ip)), 1)
        self.assertEqual(self.run_cmd(self.testvm2,
             "ping -W 1 -n -c 1 {}".format(self.testvm1.ip)), 1)
