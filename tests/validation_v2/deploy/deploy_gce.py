import argparse
import subprocess as sub
from tests.validation_v2.cattlevalidationtest.core.common_fixtures import *  # NOQA


def deploy_gce():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', help='cluster name')
    parser.add_argument('-n', help='number of nodes')
    parser.add_argument('-s', help='server image')
    parser.add_argument('-p', help='priviliged')
    args = parser.parse_args()

    print args.c, args.n, args.s, args.p

    cmd = 'gce-10acre-ranch -c ' + (args.c) + ' -n '\
          + (args.n) + ' -s ' + (args.s) + ' -p ' + args.p
    logger.info(cmd)
    process = sub.Popen(cmd, shell=True, stdin=sub.PIPE, stdout=sub.PIPE)
    process.wait()
    logger.info(process.returncode)
    return process.returncode


def list_gce_nodes(cluster):
    nodes_list_cmd = 'gcloud compute instances list --project rancher-dev ' \
                     '--zone us-central1-f --regex \"' + \
                     cluster+'.*\" | grep -v ^NAME | cut -d' ' -f1'
    process = sub.Popen(
        nodes_list_cmd, shell=True, stdin=sub.PIPE, stdout=sub.PIPE)
    nodes_list = process.stdout.readline()
    print nodes_list
    return nodes_list


def delete_gce(cluster):
    nodes_list = list_gce_nodes(cluster)
    nodes_delete_cmd = 'gcloud compute instances delete --quiet' \
                       ' --project rancher-dev --zone us-central1-f ' + \
                       nodes_list
    process = sub.Popen(
        nodes_delete_cmd, shell=True, stdin=sub.PIPE, stdout=sub.PIPE)
    process.wait()
    logger.info(process.returncode)


if __name__ == "__main__":
    out = deploy_gce()
    logger.info("Deployment Passed") if out == 0 else logger.info(
        "Deployment Failed")
    # list_gce_nodes("aruntesting0350rc1")
