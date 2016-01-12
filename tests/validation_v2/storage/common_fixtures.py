import pytest
import random
import requests
import os
import sys
import time
import logging
import paramiko
import inspect
import re
from docker import Client
import pickle

# PYTHONPATH="$PYTHONPATH:/usr/local/rancher/libs/block:/usr/local/rancher/protobuf" python2.7 /usr/local/rancher/cli/replica.py
CONTROLLER = os.environ.get('CONTROLLER_HOST')
REPLICA1 = os.environ.get('REPLICA1')
REPLICA2 = os.environ.get('REPLICA2')
INFRA_IMAGE_UUID = os.environ.get('INFRA_IMAGE',
                                 'docker:rancher/infra')
DEFAULT_TIMEOUT = 45
PRIVATE_KEY_FILENAME = "/tmp/private_key_host_ssh"

REPLICA_STATES = ["In-sync", "Degraded", "critical", "offline"]


root_dir = os.environ.get('TEST_ROOT_DIR',
                          os.path.join(os.path.dirname(__file__), 'tests',
                                       'validation_v2/storage'))

log_dir = os.path.join(root_dir, 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logfile = os.path.join(log_dir, 'test.log')
FORMAT = "\n[ %(asctime)s %(levelname)s %(filename)s:%(lineno)s " \
         "- %(funcName)20s() ] %(message)s \n"
logging.basicConfig(level=logging.INFO, format=FORMAT,
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)


@pytest.fixture(scope='session')
def get_ssh_handlers():

    controller = os.environ.get('CONTROLLER_HOST')
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
            privatekeyfile = os.path.expanduser('~/.ssh/arun_do_pvt_key')
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
        cmd = "sudo docker ps"
        # Send the command (non-blocking)
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)
    except:
        logger.info("Execution of cmd %s failed", cmd)
