#!/usr/bin/env python3

# Copyright (c) 2024 InfraMatrix. All rights reserved.

# The user ("Licensee") is hereby granted permission to use this software and
# associated documentation files (the "Software"),
# subject to the express condition that Licensee shall not, under any circumstances,
# redistribute, sublicense, copy, transfer, publish, disseminate, transmit,
# broadcast, sell, lease, rent, share, loan, or otherwise make available the
# Software, in whole or in part, in any form or by any means, to any third party
# without prior written consent from the copyright holder,
# and any such unauthorized distribution shall constitute a material breach of this
# license and result in immediate, automatic termination of all rights granted
# hereunder.

import time
import socket
import select
import sys

from .generated import compute_pb2, compute_pb2_grpc

def pick_vm(stub=None, status=None, action=""):

    request = compute_pb2.GetVMSRequest(status=status)
    response = stub.GetVMS(request)

    vms = response.vm_names
    num_vms = len(vms)

    if (num_vms == 0):

        print(f"No VMs to {action}\n")

        return -1

    vm_num = -1
    while (vm_num < 0 or vm_num > num_vms):

        print(f"Input the VM that you want to {action}:")

        for i in range(1, num_vms + 1):

            print(f"{i}: {vms[i-1]}")

        vm_num = int(input("")) - 1

    return vm_num

def process_compute_command(cmd="", stub=None):

    if (cmd == "1"):

        request = compute_pb2.CreateVMRequest()
        response = stub.CreateVM(request)

        print(f"VM Created: {response.vm_name}")

    elif (cmd == "2"):

        vm_num = pick_vm(stub=stub, status=1, action="delete")
        if (vm_num == -1):

            return

        request = compute_pb2.DeleteVMRequest(vm_number=vm_num)
        response = stub.DeleteVM(request)

        print(f"VM Deleted: {response.vm_name}")

    elif (cmd == "3"):

        vm_num = pick_vm(stub=stub, status=2, action="start")
        if (vm_num == -1):

            return

        request = compute_pb2.StartVMRequest(vm_number=vm_num)
        response = stub.StartVM(request)

        print(f"VM Started: {response.vm_name}")

    elif (cmd == "4"):

        vm_num = pick_vm(stub=stub, status=3, action="shut down")
        if (vm_num == -1):

            return

        request = compute_pb2.ShutdownVMRequest(vm_number=vm_num)
        response = stub.ShutdownVM(request)

        print(f"VM Shut Down: {response.vm_name}")

    elif (cmd == "5"):

        vm_num = pick_vm(stub=stub, status=4, action="resume")
        if (vm_num == -1):

            return

        request = compute_pb2.ResumeVMRequest(vm_number=vm_num)
        response = stub.ResumeVM(request)

        print(f"VM Resumed: {response.vm_name}")

    elif (cmd == "6"):

        vm_num = pick_vm(stub=stub, status=5, action="stop")
        if (vm_num == -1):

            return

        request = compute_pb2.StopVMRequest(vm_number=vm_num)
        response = stub.StopVM(request)

        print(f"VM Stopped: {response.vm_name}")

    elif (cmd == "7"):

        vm_num = pick_vm(stub=stub, status=5, action="monitor its status")
        if (vm_num == -1):

            return

        request = compute_pb2.GetVMStatusRequest(vm_number=vm_num)
        response = stub.GetVMStatus(request)

        print(f"VM Status: {response.vm_status}")

    elif (cmd == "8"):

        vm_num = pick_vm(stub=stub, status=5, action="connect to")
        if (vm_num == -1):

            return

        request = compute_pb2.StartPTYConnectionRequest(vm_number=vm_num)
        response = stub.StartPTYConnection(request)

        print("Connecting to server\n")

        time.sleep(1)

        client = socket.socket()
        client.connect(("0.0.0.0", 9001))

        client.send(b"\n")

        print("Connected to server, patching you into the VM\n")

        continue_processing = True
        while continue_processing:

            try:

                fds, _, _ = select.select([sys.stdin, client], [], [], 0.1)
 
                for fd in fds:

                    if fd is sys.stdin:
 
                        data = sys.stdin.buffer.read1(1024)
                        if data:

                            client.send(data)

                    else:

                        data = client.recv(1024)
                        if data:

                            sys.stdout.buffer.write(data)

                        sys.stdout.buffer.flush()

            except KeyboardInterrupt:

                client.send(b"exit\n\n")

                continue_processing = False

        client.close()

    else:

        print("Exiting")

    print("\n")
