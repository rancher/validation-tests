import argparse
import requests
import time
import paramiko
import os
import logging
import sys

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', help='target version')
    parser.add_argument('-s', help='server node')
    parser.add_argument('-u', help='ssh username of rancher server host')
    parser.add_argument('-i', help='ssh key path', default="~/.ssh/id_rsa")
    parser.add_argument('-o', help='timeout duration for rancher server to be ready', default=90)
    args = parser.parse_args()
    logger.info(args)
    logger.setLevel(logging.INFO)
    upgrade(args.t, args.s, args.u, args.i, args.o)

def upgrade(target, servernode, username, keypath, timeout):

    logger.info("UPGRADING RANCHER SERVER TO TARGET")

    i = 1
    #
    # Try to connect to the host.
    # Retry a few times if it fails.
    #
    while True:
        logger.info("Trying to connect to %s (%i/30)", servernode, i)
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            privatekeyfile = os.path.expanduser(keypath)
            mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
            ssh.connect(servernode, username=username, pkey=mykey)
            logger.info("Connected to %s", servernode)
            break
        except paramiko.AuthenticationException:
            logger.info("Authentication failed when connecting to %s",
                        servernode)
            sys.exit(1)
        except:
            logger.info("Could not SSH to %s, waiting for it to start",
                        servernode)
            i += 1
            time.sleep(2)

        # If we could not connect within time limit
        if i == 30:
            logger.info("Could not connect to %s. Giving up. "
                        "Please check private key file.", servernode)
            ssh.close()
            sys.exit(1)
    try:
        cmd = "sudo docker ps"
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info("response of cmd %s is: %s", cmd, response)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker stop $(sudo docker ps -q | awk '{print $1}')"
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        server_container_id = stdout.readlines()[0].strip("\n")
        logger.info(server_container_id)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker ps -a | awk ' NR>1 {print $2}' | cut -d \: -f 2"

        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        tag_of_previous_rancher_server = stdout.readlines()[0].strip("\n")
        logger.info("tag_of_previous_rancher_server is: %s,",
                    tag_of_previous_rancher_server)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker create --volumes-from " + server_container_id + \
              " --name rancher-data rancher/server:" \
              + tag_of_previous_rancher_server
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info("response of cmd %s is: %s", cmd, response)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker pull rancher/server:" + target
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info("response of cmd %s is: %s", cmd, response)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker run -d --volumes-from rancher-data " \
              "--restart=always -p 8080:8080 rancher/server:" + target
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info("response of cmd %s is: %s", cmd, response)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker ps | awk ' NR>1 {print $2}' | cut -d \: -f 2"
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        tag_of_rancher_version_after_upgrade = \
            stdout.readlines()[0].strip("\n")
        logger.info("tag_of_rancher_version_after_upgrade is: %s",
                    tag_of_rancher_version_after_upgrade)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker ps | awk ' NR>1 {print $8}' "
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        state_of_rancher_server_container_after_upgrade = \
            stdout.readlines()[0].strip("\n")
        logger.info("state_of_rancher_server_container_after_upgrade is: %s",
                    state_of_rancher_server_container_after_upgrade)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    time.sleep(int(timeout))

    if tag_of_rancher_version_after_upgrade == target and \
            state_of_rancher_server_container_after_upgrade == "Up":
        server = 'http://' + servernode + ":8080"
        if requests.get(server).status_code == 200:
            logger.info(
                "UPGRADE RANCHER SERVER TO TARGET COMPLETE AND SUCCESSFUL")

    ssh.close()

if __name__ == '__main__':
    logging.info("Starting upgrade tool...")
    main()
