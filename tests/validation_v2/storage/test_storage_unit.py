#!/usr/bin/python

import time
import errno
import subprocess
import os
import random
from socket import error as socket_error
from datetime import datetime, timedelta
import sys
import block_pb2
import argparse
import replica
import resource


def log(msg):
    sys.stdout.write(datetime.now().strftime("%H:%M:%S : ") + msg + "\n")


def real_sleep(amount):
    start = datetime.now()
    time.sleep(amount)
    end = datetime.now()
    delta = end - start
    deltatime = delta.seconds + (float(delta.microseconds) / 1000000)
    if deltatime < amount:
        real_sleep(amount - deltatime)


# Shutdown the world : either fully or individually
def shutdown():
    log('Shutting down ' + str(len(daemons)) + ' daemons...')
    for name in daemons.keys():
        shutdown_one(name)


def shutdown_one(name):
    rv = 0
    assert (name in daemons.keys())
    log("Terminating " + name)
    daemons[name].terminate()
    rc = daemons[name].communicate()
    if rc != (None, None):
        sys.stderr.write(
            "error: " + name + " terminated with " + str(rc) + "\n")
        rv = rc
    del daemons[name]
    return rv


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
        # log("CLI command failed due to a socker error: " + str(e))
        # log("\tcommand: " + str(commands))
        return None

    return rv


def poll_replica(rport):
    # poll for the connection. This happens very quickly on a clean volume, yet
    # takes a while to mount an existing one.
    # (that happens with manual runs when the human forgets to
    #  run "rm -f big*")
    retries = 0
    while True:
        if retries > 150:
            log("The replica never came online...")
            return False

        rv = invoke_cli(["status"], rport)
        if rv and rv["online"]:
            log("The replica is online!")
            break

        real_sleep(0.2)
        retries += 1

    return True


def create_replica(number):
    replica_name = "replica" + str(number)
    big_name = 'big' + str(number)
    command = 'ulimit -c unlimited;' + \
              './apps/replica/replica -n ' + big_name + \
              ' --create --size ' + args.rsize + \
              ' --slab ' + args.rslab + \
              ' --port ' + str(rport[number])
    daemons[replica_name] = subprocess.Popen(command, shell=True)


# Choose random replicas to kill & attempt to relaunch them
def kill_replicas(relaunch_when):
    s = set(range(0, replica_count))
    log("Beginning scheduled kills & relaunches")
    for i in range(0, args.kill):
        removed = random.choice(list(s))
        s.remove(removed)
        removed += 1

        replica_name = "replica" + str(removed)
        big_name = "big" + str(removed)

        rv = shutdown_one(replica_name)

        # Future case to consider: might need to relaunch at a later time
        if relaunch_when == 'relaunch_now':
            relaunch_replicas(replica_name, big_name, removed)


def relaunch_replicas(replica_name, big_name, removed):
    print ("\n")
    log("Relaunching lost replica: " + replica_name + "...")
    command = 'ulimit -c unlimited;' + \
              './apps/replica/replica -n ' + big_name + \
              '--port ' + str(rport[removed])
    daemons[replica_name] = subprocess.Popen(command, shell=True)
    poll_replica(rport[removed])


# Preliminary time keeping and cleaning
start_time = datetime.now()


log('Removing old big files...')
os.system("rm -f big*")

# Lets get the generated protobuf code
#  - this thing must be run from the $objdir
sys.path.append('libs/block')
sys.path.append('3rd-party/protobuf/python')

# Parse script arguments

parser = argparse.ArgumentParser(description='Run system test on replicas.')
parser.add_argument(
    "-r", "--replicas",
    help="the number of replicas initially created [must be > 1], "
    "note: an extra final replica is always created",
    type=int, default=2)
parser.add_argument(
    "-k", "--kill",
    help="kill random replicas abruptly and attempt to relaunch",
    type=int, default=0)
parser.add_argument("-kc", "--killcase",
                    help="choose case for terminating a replica",
                    type=str, default="basic",
                    choices=["basic", "under_load", "pre_negotiating_st",
                             "insync_st"])
parser.add_argument("-ls", "--livesnap",
                    help="toggle live snapshots [off by default]",
                    dest='livesnap', action='store_true', default=False)
parser.add_argument("--rsize", help="declare size of replica [20G by default]",
                    type=str,
                    default='20G')
parser.add_argument("--rslab", help="declare size of slabs [1G by default]",
                    type=str,
                    default='1G')
parser.add_argument("-w", "--web",
                    help="use the web and declare mb size of download"
                         "[5 by default]", type=int,
                    choices=[5, 10, 20, 50, 100], default=5)
parser.add_argument("-dd", "--diskdump",
                    help="use dd and declare count of 4096b blocks"
                         " like 1 for 1 block", type=int,
                    choices=[1, 10, 100, 500, 1000, 5000])
args = parser.parse_args()

if args.replicas < 2:
    sys.exit('Number of replicas is less than 2, exiting')

# The CLI script - lets use it as a module
sys.path.append('cli')


def die(daemons, msg):
    for (name, process) in daemons.iteritems():
        process.terminate()
        process.wait()

    sys.exit(msg)

resource.setrlimit(resource.RLIMIT_CORE, (-1, -1))

# Initialize the ports
replica_count = args.replicas
rport = dict()
# this point is moot as each socket lives within its own namespace
rport[1] = 6000 + random.randrange(0, 100)

for i in range(1, replica_count):
    rport[i + 1] = rport[1] + i

cport = rport[1] - 1

# yet it will help if we start sharing VMs
log("Using rport[1]=" + str(rport[1]))

#
# Start the replica daemons
#
daemons = {}
for i in range(0, replica_count):
    create_replica(i + 1)
    poll_replica(rport[i + 1])

#
# Start the client daemon
#
client_rports = list()
for value in rport.keys():
    client_rports.append('-h')
    client_rports.append('localhost:' + str(rport[value]))

command = 'ulimit -c unlimited;' + \
          './apps/controller/controller ' + ' '.join(
            client_rports) + ' -m ' + str(cport)
daemons["client"] = subprocess.Popen(command, shell=True)

# During registering of replicas (post registration, before NegotiatingSt)
if args.killcase == "pre_negotiating_st":
    kill_replicas('relaunch_now')

if daemons["client"].poll():
    die(daemons, "client has terminated...")

real_sleep(2)

# During InSync
rval = invoke_cli(["controller-status"], cport)
log('Controller status is: ' + str(rval["controller-status"]))

#
# NBD runs as root and detaches/terminates itself
#
nbd_dev = ""
for i in range(0, 10):
    nbd_dev = '/dev/nbd' + str(i)
    nbd = subprocess.Popen(['sudo', 'nbd-client', '-c', nbd_dev],
                           stdout=subprocess.PIPE)

    # Find the disconnected device (it does not print the PID)
    if not nbd.stdout.readline():
        log("Using " + nbd_dev)
        nbd = subprocess.Popen(
            ['sudo', 'nbd-client', '-b', '4096', 'localhost', nbd_dev,
             '-N', 'disk', '-n'])
        break

if nbd.poll():
    die(daemons, "nbd-client has terminated...")

#
# Poll for the device to come online
#
got_size = False
for i in range(1, 30):
    dev = subprocess.Popen(['sudo', 'blockdev', '--getsize', nbd_dev])
    if dev.wait() == 0:
        got_size = True
        break
    real_sleep(1)
if not got_size:
    shutdown()
    os.system("sudo kill %s" % (nbd.pid))
    sys.exit("Device never came online")

#
# Format the block dev as ext4
#
cmd = subprocess.Popen(['sudo', 'mkfs.ext4', '-b', '4096', nbd_dev])
rc = cmd.wait()
if rc != 0:
    shutdown()
    os.system("sudo kill %s" % (nbd.pid))
    sys.exit(rc)

# Take first snap
snapcount = 1
log('Taking first snap ' + str(snapcount))
if not invoke_cli(["snap", "s1"], cport):
    shutdown()
    os.system("sudo kill %s" % (nbd.pid))
    sys.exit(-1)
snapcount += 1

#
# Mount the new filesystem
#
if not os.path.exists("newfs"):
    os.makedirs("newfs")
cmd = subprocess.Popen(['sudo', 'mount', nbd_dev, 'newfs'])
rc = cmd.wait()
if rc != 0:
    log("Error: failed to mount the filesystem")
    shutdown()
    os.system("sudo kill %s" % (nbd.pid))
    sys.exit(rc)

orig_wd = os.getcwd()
os.chdir("newfs")

#
# Dump some data into the filesystem
#
log('Beginning data dump...')
if args.diskdump:
    cmd = subprocess.Popen(['dd', 'if=/dev/zero', 'of=testfile', 'bs=4096',
                            'count=' + str(args.diskdump), 'conv=fdatasync',
                            'oflag=direct'])
else:
    cmd = subprocess.Popen(['sudo', 'wget',
                            'http://www.web4host.net/' + str(
                                args.web) + 'MB.zip'])

# Take live snaps or initiate live kills, if enabled
if args.livesnap or args.killcase == "under_load":
    while str(cmd.poll()) == "None":
        log('Taking live snap ' + str(snapcount))
        invoke_cli(["snap", "s" + str(snapcount) + "live"], cport)
        snapcount += 1
        real_sleep(1)
        if args.killcase == "under_load":
            kill_replicas('relaunch_now')
            break

rc = cmd.wait()
log('Done with data dump')
if rc != 0:
    shutdown()
    os.system("sudo kill %s" % (nbd.pid))
    sys.exit(rc)

log('Taking inconsistent snap ' + str(snapcount))
invoke_cli(["snap", "s" + str(snapcount) + "inconsistent"], cport)
snapcount += 1
rv = 0

#
# Unmount the new filesystem
#
log('Running "sync"...')
cmd = subprocess.Popen(['sudo', 'sync'])
if cmd.wait() != 0:
    rv = cmd.returncode

# Take another snap
log('Taking snap ' + str(snapcount))
invoke_cli(["snap", "s" + str(snapcount)], cport)
snapcount += 1

log('Running "umount"...')
os.chdir(orig_wd)
cmd = subprocess.Popen(['sudo', 'umount', 'newfs'])
if cmd.wait() != 0:
    rv = cmd.returncode

# Take the final snap
log('Taking final snap ' + str(snapcount))
invoke_cli(["snap", "s" + str(snapcount) + "-final"], cport)

# Bring up another final replica to rebuild
rport[replica_count + 1] = rport[replica_count] + 1
create_replica(replica_count + 1)
poll_replica(rport[replica_count + 1])
log('Rebuilding the replica: replica' + str(replica_count + 1) + '...')
invoke_cli(["rebuild", "localhost", str(cport)], rport[replica_count + 1])

#
# Splice the final replica in and wait for the rebuild
#
cli_rv = None
if rv == 0:
    cli_rv = invoke_cli(
        ["connect", "localhost", str(rport[replica_count + 1])], cport)

if cli_rv:
    retries = 0
    while True:
        if retries > 90:
            log("Error: the connection process never completed")
            rv = -1
            break

        rval = invoke_cli(["replicas"], cport)
        if rval and len(rval) == 2:
            have_splicing = False
            for (host, port, status) in rval["replicas"]:
                if status != "Online":
                    have_splicing = True
            if not have_splicing:
                log("Controller is connected! " + str(
                    len(rval["replicas"])) + " replicas are online.")
                break

        real_sleep(1)
        retries += 1
else:
    log('error: "connect" was refused (or was not attempted)')

# Kill case that should always work
if args.killcase == "basic":
    kill_replicas('relaunch_now')

#
# Shutdown the world
#
if rv == 0:
    log('All is well!')
    rv = shutdown()
else:
    shutdown()

log('Killing "nbdclient"...\n')
os.system("sudo kill %s" % (nbd.pid))

elapsed_time = datetime.now() - start_time
log('Total elapsed time for this run: ' + str(
    elapsed_time.seconds) + '.' + str(
    elapsed_time.microseconds / 1000) + ' seconds.')

log('Done. Exiting...\n')
sys.exit(rv)
