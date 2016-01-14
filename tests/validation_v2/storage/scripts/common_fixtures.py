import os
import logging
import pytest
import paramiko
import sys
import time
import time, errno, subprocess, os, random, datetime
from socket import error as socket_error
from time import localtime, strftime
from datetime import datetime, timedelta

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


def connect(host):
    i = 1
    #
    # Try to connect to the host.
    # Retry a few times if it fails.
    #
    while True:
        logger.info("Trying to connect to %s (%i/30)", host, i)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            privatekeyfile = os.path.expanduser('~/.ssh/id_rsa')
            mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
            ssh.connect(host, username='root', pkey=mykey)
            logger.info("Connected to %s", host)
            break
        except paramiko.AuthenticationException:
            logger.info("Authentication failed when connecting to %s",
                        host)
            sys.exit(1)
        except:
            logger.info("Could not SSH to %s, waiting for it to start",
                        host)
            i += 1
            time.sleep(2)

        # If we could not connect within time limit
        if i == 30:
            logger.info("Could not connect to %s. Giving up. "
                        "Please check private key file.", host)
            ssh.close()
            sys.exit(1)

    return ssh


def invoke_cli(commands, rport):
    c = replica.Connection(False)
    try:
        c.connect("localhost", rport)
        rv = c.invoke(commands)
        if not rv["success"]:
            log("CLI command failed: " + rv["error_message"])
            log("\tcommand: " + str(commands))
            return None
    except socket_error as e:
        #log("CLI command failed due to a socker error: " + str(e))
        #log("\tcommand: " + str(commands))
        return None

    return rv