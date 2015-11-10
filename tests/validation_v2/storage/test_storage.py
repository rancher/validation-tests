# import time
# import errno
# import subprocess
# import os
# import random
# from socket import error as socket_error
# from datetime import datetime, timedelta
# import sys
# import block_pb2
# import argparse
# import replica
# import resource
from docker import Client
from common_fixtures import *
import paramiko
import os
import json
import time

# docker pull rancher/infra:1026-cli-os
# get container id from above command
# enter the container - docker exec -it <id> bash
# execute below command inside container -
# PYTHONPATH="$PYTHONPATH:/usr/local/rancher/libs/block:/usr/local/rancher/protobuf" python2.7 /usr/local/rancher/cli/replica.py
# sudo apt-get install --reinstall python-pkg-resources


def install_infra():
    servernode = '104.197.138.118'
    username = 'aruneli'
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privatekeyfile = os.path.expanduser('~/.ssh/google_compute_engine')
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    ssh.connect(servernode, username=username, pkey=mykey)
    logger.info("Connected to %s", servernode)
    c = Client(base_url='unix://var/run/docker.sock')
    for line in c.pull('busybox', stream=True):
        print(json.dumps(json.loads(line), indent=4))
    time.sleep(20)
    id = c.containers(quiet=True, latest=True)[0]['Id']
    print id
    return id, ssh


def test_create_replica():
    # container_id, ssh = install_infra()
    # cmd = "sudo docker exec -it bash "+container_id
    # # Send the command (non-blocking)
    servernode = "104.197.138.118"
    username = "aruneli"
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    privatekeyfile = os.path.expanduser('~/.ssh/google_compute_engine')
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    ssh.connect(servernode, username=username, pkey=mykey)
    logger.info("Connected to %s", servernode)
    #
    # cmd = "sudo docker pull rancher/infra:1026-cli-os"
    # logger.info("command being executed %s:", cmd)
    # stdin, stdout, stderr = ssh.exec_command(cmd)
    # response = stdout.readlines()
    # logger.info(response)
    # time.sleep(20)

    # cmd = "sudo docker images"
    # logger.info("command being executed %s:", cmd)
    # stdin, stdout, stderr = ssh.exec_command(cmd)
    # response = stdout.readlines()
    # logger.info(response)
    # id = response[1].split()[2]
    # logger.info("id is %s", id)

    # cmd = "sudo docker exec -it d7686400c1fa bash"
    # logger.info("command being executed %s:", cmd)
    # stdin, stdout, stderr = ssh.exec_command(cmd)
    # response = stdout.readlines()
    # logger.info(response)

    from docker import Client
    c = Client(base_url='unix://var/run/docker.sock')
    executor = c.exec_create('d7686400c1fa', cmd='df')
    response = c.exec_start(executor.get('Id'))
    logger.info(response)
