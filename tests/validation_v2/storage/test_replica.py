import logging
import subprocess
import pytest
import os
import paramiko
import sys
import time
import docker

FORMAT = "\n[ %(asctime)s %(levelname)s %(filename)s:%(lineno)s " \
         "- %(funcName)20s() ] %(message)s \n"
logging.basicConfig(level=logging.INFO, format=FORMAT,
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)

def test_get_ssh_handlers():

    controller = os.environ.get('CONTROLLER')
    replica1 = os.environ.get('REPLICA1')
    replica2 = os.environ.get('REPLICA2')
    i = 1
    #
    # Try to connect to the host.
    # Retry a few times if it fails.
    #
    while True:
        logger.info("Trying to connect to %s (%i/30)", controller, i)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            privatekeyfile = os.path.expanduser('~/.ssh/id_rsa')
            mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
            ssh.connect(controller, username='root', pkey=mykey)
            logger.info("Connected to %s", controller)
            break
        except paramiko.AuthenticationException:
            logger.info("Authentication failed when connecting to %s",
                        controller)
            sys.exit(1)
        except:
            logger.info("Could not SSH to %s, waiting for it to start",
                        controller)
            i += 1
            time.sleep(2)

        # If we could not connect within time limit
        if i == 30:
            logger.info("Could not connect to %s. Giving up. "
                        "Please check private key file.", controller)
            ssh.close()
            sys.exit(1)
    try:
        cmd = "docker ps"
        # Send the command (non-blocking)
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        cmd = 'docker exec -i 5f sh -c "PYTHONPATH="$PYTHONPATH:/usr/local/rancher/libs/block:/usr/local/rancher/protobuf" python2.7 /usr/local/rancher/cli/replica.py"'
        # Send the command (non-blocking)
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        logger.info(stderr.readlines())

        cmd = 'docker exec -i 5f sh -c ""'
        # Send the command (non-blocking)
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        logger.info(stderr.readlines()

    except:
        logger.info("Execution of cmd %s failed", cmd)


# def run_command(command):
#     p = subprocess.Popen(command,
#                          stdout=subprocess.PIPE,
#                          stderr=subprocess.STDOUT)
#     return iter(p.stdout.readline, b'')
#
#
# def test_create_replica_1():
#         name = "test1"
#         volume_size = "10000000000"
#         slab_size = "1000000000"
#         port = "5000"
#
#         # with open('replica.test.log', 'w'): pass
#         cmd = "/usr/local/bin/replica -n test -c -s "+volume_size+" -l "+slab_size+" -p "+port+" &"
#         print cmd
#         command = 'python /usr/local/rancher/cli/replica.py -a localhost -p 5000 status'.split()
#         lines = []
#         for line in run_command(command):
#                 print(line)
#                 lines.append(line)
#         assert "online" in lines
#
#
# def test_kill_replica_and_relaunch():
#         name = "test1"
#         volume_size = "60000000000"
#         slab_size = "6000000000"
#         port = "5000"
#
#         # with open('replica.test.log', 'w'): pass
#         cmd = "/usr/local/bin/replica -n test -c -s "+volume_size+" -l "+slab_size+" -p "+port+" &"
#         print cmd
#         command = 'python /usr/local/rancher/cli/replica.py -a localhost -p 5005 status'.split()
#         lines = []
#         for line in run_command(command):
#                 print(line)
#                 lines.append(line)
#         assert "online" in lines
#         # To Do
#         # kill created replica and relaunch
#
# def test_take_snap():
#         name = "test1"
#         volume_size = "60000000000"
#         slab_size = "6000000000"
#         port = "5000"
#
#         # with open('replica.test.log', 'w'): pass
#         cmd = "/usr/local/bin/replica -n test -c -s "+volume_size+" -l "+slab_size+" -p "+port+" &"
#         print cmd
#         command = 'python /usr/local/rancher/cli/replica.py -a localhost -p 5005 status'.split()
#         lines = []
#         for line in run_command(command):
#                 print(line)
#                 lines.append(line)
#         assert "online" in lines
#         # To Do
#         # Take snap
#         # list snapshots and assert
#
#
# def test_replica_capabilities():
#         name = "test1"
#         volume_size = "60000000000"
#         slab_size = "6000000000"
#         port = "5000"
#
#         # with open('replica.test.log', 'w'): pass
#         cmd = "/usr/local/bin/replica -n test -c -s "+volume_size+" -l "+slab_size+" -p "+port+" &"
#         print cmd
#         command = 'python /usr/local/rancher/cli/replica.py -a localhost -p 5005 capabilities'.split()
#         lines = []
#         for line in run_command(command):
#                 print(line)
#                 lines.append(line)
#         assert "online" in lines
#
# def test_controller_status():
#
#         cmd = "/usr/local/bin/replica -n test -c -s "+volume_size+" -l "+slab_size+" -p "+port+" &"
#         print cmd
#         command = 'python /usr/local/rancher/cli/replica.py -a localhost -p 5005 capabilities'.split()
#         lines = []
#         for line in run_command(command):
#                 print(line)
#                 lines.append(line)
#         assert "online" in lines
#
#
# def test_dump_volume():
#
#
# def test_load_volume();