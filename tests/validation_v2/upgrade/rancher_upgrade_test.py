# How to Launch:
# Example: <validation-tests>/v2/tests/upgrade/rancher_upgrade_test.py
# -b 0.37.0 -t 0.37.1 -s 104.197.121.156 -u aruneli
# base version has no significance now, but target version should be a
# valid rancher server version
# server option (-s): IP Address of the rancher server
# username is the username with which you ssh to your GCE instance

from common_fixtures import *  # NOQA
import argparse
import os
import paramiko
import requests
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', help='base version')
    parser.add_argument('-t', help='target version')
    parser.add_argument('-s', help='server node')
    parser.add_argument('-u', help='ssh username of rancher server host')
    parser.add_argument('-script',
                        help='provide the script or give "/" for all tests')

    args = parser.parse_args()

    tmp_dir = os.path.join(root_dir, 'tmp')
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    logger.info("tmp_dir is: %s", tmp_dir)

    core_dir = os.path.join(root_dir, 'cattlevalidationtest', 'core')
    logger.info("core_dir is: %s", core_dir)

    core_target_checkedout_dir = os.path.join(
        tmp_dir, 'rancher-tests', 'tests', 'validation_v2',
        'cattlevalidationtest', 'core')
    if not os.path.exists(core_target_checkedout_dir):
        os.makedirs(core_target_checkedout_dir)
    logger.info("core_target_checkedout_dir : %s", core_target_checkedout_dir)

    core_target_dir = os.path.join(root_dir, 'cattlevalidationtest',
                                   'core_target')
    if not os.path.exists(core_target_dir):
        os.makedirs(core_target_dir)
    logger.info("core_target_dir is: %s", core_target_dir)

    upgrade_test(args.b, args.t, args.s, args.u, tmp_dir, core_dir,
                 core_target_dir, core_target_checkedout_dir, args.script)


def upgrade_test(base, target, servernode, username, tmp_dir, core_dir,
                 core_target_dir, core_target_checkedout_dir, script_to_test):
    logger.info("CREATING SERVICES NOW IN BASE SETUP...")
    # create_cmd = "py.test " + core_dir + "/ -v -m create -s"
    create_cmd = "py.test " + core_dir + script_to_test+" -v -m create -s"

    logger.info("create command is: %s", create_cmd)

    os.system(create_cmd)

    upgrade_rancher_server(base, target, servernode, username)
    # below one line is temporary until we start having real tagged versions
    os.system(("cp -r " + core_dir + "/*.py " + tmp_dir))
    # os.system("git clone -b master --single-branch "
    #           "https://github.com/aruneli/rancher-tests.git")
    logger.info("COPYING TARGET LIBRARIES in core_target folder...")

    os.system(("cp -r " + tmp_dir + "/test_*.py " + core_target_dir))
    os.system(("cp -r " + tmp_dir + "/common_fixtures.py " + core_target_dir))

    logger.info("VALIDATING UPGRADED SETUP NOW WITH TARGET")

    # validate_cmd = "py.test " + core_target_dir + "/ -v -m validate -s"
    validate_cmd =\
        "py.test " + core_target_dir + script_to_test+" -v -m validate -s"
    logger.info(validate_cmd)

    os.system(validate_cmd)
    logger.info("VALIDATION COMPLETE")

    os.system("rm -rf " + tmp_dir + "/*")
    os.system("rm -rf " + core_target_dir + "/*")


def upgrade_rancher_server(base, target, servernode, username):
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
            privatekeyfile = os.path.expanduser('~/.ssh/google_compute_engine')
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
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)
    except:
        logger.info("Execution of cmd %s failed", cmd)

    try:
        cmd = "sudo docker stop $(sudo docker ps -q | awk '{print $1}')"
        # Send the command (non-blocking)
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        server_container_id = stdout.readlines()[0].strip("\n")
        logger.info(server_container_id)

        cmd = "sudo docker ps -a | awk ' NR>1 {print $2}' | cut -d \: -f 2" \
              " | cut -d \\v -f 2"
        # Send the command (non-blocking)
        logger.info("command being executed %s:", cmd)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        tag_of_previous_rancher_server = stdout.readlines()[0].strip("\n")
        logger.info(tag_of_previous_rancher_server)

        cmd = "sudo docker create --volumes-from " + server_container_id + \
              " --name rancher-data rancher/server:v"\
              + tag_of_previous_rancher_server
        logger.info("command being executed %s:", cmd)
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        cmd = "sudo docker pull rancher/server:v" + target
        logger.info("command being executed %s:", cmd)
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        cmd = "sudo docker run -d --volumes-from rancher-data " \
              "--restart=always -p 8080:8080 rancher/server:v" + target
        logger.info("command being executed %s:", cmd)
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        response = stdout.readlines()
        logger.info(response)

        cmd = "sudo docker ps | awk ' NR>1 {print $2}' | cut -d \: -f 2| " \
              "cut -d \\v -f 2"
        logger.info("command being executed %s:", cmd)
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        tag_of_rancher_version_after_upgrade = \
            stdout.readlines()[0].strip("\n")
        logger.info("tag_of_rancher_version_after_upgrade is: %s",
                    tag_of_rancher_version_after_upgrade)

        cmd = "sudo docker ps | awk ' NR>1 {print $8}' "
        logger.info("command being executed %s:", cmd)
        # Send the command (non-blocking)
        stdin, stdout, stderr = ssh.exec_command(cmd)
        state_of_rancher_server_container_after_upgrade = \
            stdout.readlines()[0].strip("\n")
        logger.info("state_of_rancher_server_container_after_upgrade is: %s",
                    state_of_rancher_server_container_after_upgrade)

        time.sleep(90)

        if tag_of_rancher_version_after_upgrade == target and \
                state_of_rancher_server_container_after_upgrade == "Up":
            server = 'http://' + servernode + ":8080"
            if requests.get(server).status_code == 200:
                logger.info(
                    "UPGRADE RANCHER SERVER TO TARGET COMPLETE AND SUCCESSFUL")
    except:
        logger.info("Execution of cmd %s failed", cmd)

    ssh.close()

if __name__ == '__main__':
    main()
