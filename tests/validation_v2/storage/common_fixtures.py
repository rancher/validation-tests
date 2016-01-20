import logging
import os
import sys
import time
from socket import error as socket_error
import binascii
import socket
import struct
import sys
from optparse import OptionParser, OptionGroup
import block_pb2
import paramiko

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

FORMAT = "\n[ %(asctime)s %(levelname)s %(filename)s:%(lineno)s " \
         "- %(funcName)20s() ] %(message)s \n"
logging.basicConfig(level=logging.INFO, format=FORMAT,
                    datefmt='%a, %d %b %Y %H:%M:%S')
logger = logging.getLogger(__name__)

# Controller States
# Unknown = 0  Communication error
# Online = 7  The happy state ignoring rebuilds. Every known replica is online.
# Degraded = 8  There is a quorum, yet some replicas are offline
# Critical = 9  Mutations are being replicated to a subset of replicas
# Offline = 10  Unable to connect to enough replicas to establish a quorum

controller_states = {'0': 'Unknown', '7': 'Online', '8': 'Degraded',
                     '9': 'Critical', '10': 'Offline'}
replica1 = os.environ.get('REPLICA1')
replica2 = os.environ.get('REPLICA2')
replica3 = os.environ.get('REPLICA2')
controller = os.environ.get('CONTROLLER')
CPORT = 5000


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


class cleanup:

    logger.info("cleaning up the test hosts...")

    def kill_replica1(self):
        ssh_replica1 = connect(replica1)
        # kill replica 1 daemon if running, delete /replica1 folder if exists
        cmd = "docker exec -i 4d sh -c 'pkill -f replica'"
        logger.info("command being executed %s", cmd)
        ssh_replica1.exec_command(cmd)
        cmd = "docker exec -i 4d sh -c 'pgrep replica'"
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica1.exec_command(cmd)
        assert len(stdout.readlines()) == 0
        cmd = "docker exec -i 4d sh -c 'rm -rf replica1'"
        logger.info("command being executed %s", cmd)
        ssh_replica1.exec_command(cmd)
        ssh_replica1.close()

    def kill_replica2(self):
        ssh_replica2 = connect(replica2)
        # kill replica 2 daemon if running, delete /replica2 folder if exists
        cmd = 'docker exec -i f1 sh -c "pkill -f replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        logger.info(stdout.readlines)
        cmd = 'docker exec -i f1 sh -c "pgrep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica2.exec_command(cmd)
        assert len(stdout.readlines()) == 0
        cmd = "docker exec -i f1 sh -c 'rm -rf replica2'"
        logger.info("command being executed %s", cmd)
        ssh_replica2.exec_command(cmd)
        ssh_replica2.close()

    def kill_replica3(self):
        ssh_replica3 = connect(replica2)
        # kill replica 3 daemon if running, delete /replica3 folder if exists
        cmd = 'docker exec -i c4 sh -c "pkill -f replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica3.exec_command(cmd)
        logger.info(stdout.readlines)
        cmd = 'docker exec -i c4 sh -c "pgrep replica"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_replica3.exec_command(cmd)
        assert len(stdout.readlines()) == 0
        cmd = "docker exec -i c4 sh -c 'rm -rf replica3'"
        logger.info("command being executed %s", cmd)
        ssh_replica3.exec_command(cmd)
        ssh_replica3.close()

    def kill_controller(self):
        ssh_controller = connect(controller)
        # kill controller daemon if running and delete /controller
        # folder if exists
        cmd = 'docker exec -i 5f sh -c "pkill -f controller"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_controller.exec_command(cmd)
        cmd = 'docker exec -i 5f sh -c "pgrep controller"'
        logger.info("command being executed %s", cmd)
        stdin, stdout, stderr = ssh_controller.exec_command(cmd)
        logger.info(stderr.readlines())
        # assert len(stdout.readlines()) == 0
        cmd = "docker exec -i 5f sh -c 'rm -rf controller'"
        logger.info("command being executed %s", cmd)
        ssh_controller.exec_command(cmd)
        ssh_controller.close()


# uint32_t    size:21,
#             type:5,
#             _unused:6;
def compose_buf(msg):
    hdr = 0

    # type: msg=10
    hdr += (10 << 21)

    # size
    hdr += (len(msg) & 0x1fffff)

    return struct.pack('i', hdr) + msg


def compose_hdr(msg_len, type):
    hdr = 0

    hdr += (type << 21)

    # size
    hdr += (msg_len & 0x1fffff)

    return struct.pack('i', hdr)


class Connection:
    def __init__(self, debug):
        self.s_ = socket.socket()
        self.next_seq_ = 1
        self.debug_ = debug
        self.connected_ = False
        self.rw_size = 128 * 1024

    def is_connected(self):
        return self.connected_

    def connect(self, address, port):
        if self.connected_:
            return

        logger.info("Connecting to " + address + ":" + str(port) + "...")
        self.s_.connect((address, port))

        # Start with the Hello
        req = block_pb2.ClientHello()
        req.version = 1
        logger.info("Sending Hello")
        self.send(compose_buf(req.SerializeToString()))
        rx = self.s_.recv(1024)
        logger.info("Received " + str(len(rx)) + " bytes of data")
        resp = self.extract_hello(rx)
        logger.info("Connected to replica v=" + str(resp.version))
        self.connected_ = True

    def invoke(self, terms):
        # prepare the request
        logger.info("command: %s", terms[0])
        req = block_pb2.Request()
        if terms[0] == "capabilities":
            req.type = block_pb2.Request.Capabilities
        elif terms[0] == "replicas":
            req.type = block_pb2.Request.ListReplicas
        elif terms[0] == "status":
            req.type = block_pb2.Request.Status
        elif terms[0] == "snap":
            req.type = block_pb2.Request.TakeSnapshot
            if len(terms) == 1:
                sys.exit("Need a snapshot name")
            req.snapshot.name = terms[1]
        elif terms[0] == "remove-snap":
            req.type = block_pb2.Request.RemoveSnapshot
            if len(terms) == 1:
                sys.exit("Need a snapshot name")
            req.snapshot.name = terms[1]
        elif terms[0] == "list-snapshots":
            req.type = block_pb2.Request.ListSnapshots
        elif terms[0] == "changed-blocks":
            req.type = block_pb2.Request.ChangedBlocks
            if len(terms) < 2:
                sys.exit("Need a snapshot name")
            req.snapshot.name = terms[1]
        elif terms[0] == "rebuild":
            req.type = block_pb2.Request.RebuildReplica
            if len(terms) < 3:
                sys.exit("Need a <host> and <port> arguments")
            req.replica.host = terms[1]
            req.replica.port = int(terms[2])
        elif terms[0] == "connect":
            req.type = block_pb2.Request.Connect
            if len(terms) < 3:
                sys.exit("Need a <host> and <port> arguments")
            req.replica.host = terms[1]
            req.replica.port = int(terms[2])
        elif terms[0] == "replication-status":
            req.type = block_pb2.Request.ReplicationStatus
        elif terms[0] == "controller-status":
            req.type = block_pb2.Request.ControllerInfo
        else:
            sys.exit("Unrecognized command")

        req.seq = self.next_seq()

        self.send(compose_buf(req.SerializeToString()))

        rx = self.s_.recv(1024)
        self.print_dbg("Received " + str(len(rx)) + " bytes of data")

        (processed, resp) = self.extract_resp(rx)
        if terms[0] == "capabilities":
            caps = {}
            caps["success"] = True
            caps["id"] = resp.capability.id
            caps["replica_capacity"] = resp.capability.replica_capacity
            caps["replica_usage"] = resp.capability.replica_usage
            caps["volume_size"] = resp.capability.volume_size
            caps["block_size"] = resp.capability.block_size

            return caps
        elif terms[0] == "replicas":
            rv = {}
            rv["success"] = True
            rv["replicas"] = []
            for r in resp.replicas.item:
                rv["replicas"].append((r.host, r.port, ("", "Online")[r.online] + ("", "Splicing")[r.splicing]))
            return rv
        elif terms[0] == "status":
            rv = {}
            rv["success"] = True
            rv["online"] = resp.status.online
            rv["error_message"] = resp.status.error_message
            return rv
        elif terms[0] == "snap" or terms[0] == "connect":
            rv = {}
            rv["success"] = resp.io_result.success
            rv["error_message"] = resp.io_result.error_message
            return rv
        elif terms[0] == "remove-snap":
            rv = {}
            rv["success"] = resp.io_result.success
            rv["error_message"] = resp.io_result.error_message
            return rv
        elif terms[0] == "list-snapshots":
            rv = []
            for s in resp.snapshots.item:
                rv.append(dict([("name", s.name), ("id", s.id)]))
            return rv
        elif terms[0] == "controller-status":
            rv = {}
            rv["success"] = True
            rv["controller-status"] = resp.contr_info.status
            return rv
        elif terms[0] == "changed-blocks":
            rv = []
            for r in resp.ranges.item:
                rv.append((r.offset, r.size))
            return rv
        elif terms[0] == "rebuild":
            rv = {}
            rv["success"] = resp.io_result.success
            rv["error_message"] = resp.io_result.error_message
            return rv
        elif terms[0] == "replication-status":
            rv = {}
            rv["success"] = True
            rv["status"] = resp.rep_info.status
            rv["error_message"] = resp.rep_info.error_message
            return rv
        else:
            sys.stderr.write("Missing the response handler for " + terms[0])
            return None
        return

    def next_seq(self):
        rv = self.next_seq_
        self.next_seq_ += 1
        return rv

    def invoke_read(self, fname, snap = None, offset = 0, size = None):
        # get capabilities as we need the volume size
        req = block_pb2.Request()
        req.type = block_pb2.Request.Capabilities
        req.seq = self.next_seq()

        self.send(compose_buf(req.SerializeToString()))

        rx = self.s_.recv(1024)
        self.print_dbg("Received " + str(len(rx)) + " bytes of data")

        (processed, resp) = self.extract_resp(rx)
        volume_size = resp.capability.volume_size
        if offset == None:
            offset = 0
        if size == None:
            size = volume_size - offset
        if size < 0 or offset < 0 or offset + size > volume_size:
                sys.exit("Bad offset and size values")

        # prep the file
        file = open(fname, "wb")
        if not file:
            sys.exit("Failed to open file: " + fname)

        # now read the data up to 128 kB at a time
        off = offset
        while off < offset + size:
            to_read = min(offset + size - off, self.rw_size)

            req = block_pb2.Request()
            req.type = block_pb2.Request.Read
            req.seq = self.next_seq()
            req.range.offset = off
            req.range.size = to_read
            if snap:
                req.range.snapshot = snap

            # Request the data
            self.send(compose_buf(req.SerializeToString()))
            rx = self.recv(1000)

            # Process the (structured) response header
            (processed, resp) = self.extract_resp(rx)
            if not resp.io_result.success:
                sys.exit("Read failed: " + resp.io_result.error_message)

            # Process the (unstructured data) header
            (header_size, data_size, rx) = self.extract_buf(rx[processed:])
            self.print_dbg("Getting " + str(data_size) + " bytes of data")
            assert(data_size == to_read)

            # Dump the first few bytes to disk
            file.write(rx)
            self.print_dbg("written," + str(len(rx)))
            written = len(rx)

            while written < to_read:
                rx = self.s_.recv(64 * 1024)
                file.write(rx)
                self.print_dbg("written," + str(len(rx)))
                written += len(rx)

            off += to_read
        file.close()
        return

    def invoke_write(self, fname, offset = 0, size = None):
        # get capabilities as we need the volume size
        req = block_pb2.Request()
        req.type = block_pb2.Request.Capabilities
        req.seq = self.next_seq()

        self.send(compose_buf(req.SerializeToString()))

        rx = self.s_.recv(1024)
        self.print_dbg("Received " + str(len(rx)) + " bytes of data")

        (processed, resp) = self.extract_resp(rx)
        volume_size = resp.capability.volume_size
        if offset == None:
            offset = 0
        if size == None:
            size = volume_size - offset
        if size < 0 or offset < 0 or offset + size > volume_size:
                sys.exit("Bad offset and size values")

        # prep the file
        file = open(fname, "rb")
        if not file:
            sys.exit("Failed to open file: " + fname)

        # now write the data up to 128 kB at a time
        off = offset
        while off < offset + size:
            to_write = min(offset + size - off, self.rw_size)

            req = block_pb2.Request()
            req.type = block_pb2.Request.Write
            req.seq = self.next_seq()
            req.range.offset = off
            req.range.size = to_write

            # Push the data out into two parts: the protobuf message that
            # describes the operation and the data payload
            self.send(compose_buf(req.SerializeToString()))
            self.send(compose_hdr(to_write, 11))
            data = file.read(to_write)
            if len(data) != to_write:
                sys.exit("Failed to read expected number of bytes from file")

            self.send(data)

            rx = self.s_.recv(1024)
            self.print_dbg("Received " + str(len(rx)) + " bytes of data")

            # Process the (structured) response header
            (processed, resp) = self.extract_resp(rx)
            if not resp.io_result.success:
                sys.exit("Write failed: " + resp.io_result.error_message)

            off += to_write
        file.close()
        return

    def send(self, buf):
        self.print_dbg("data: " + binascii.hexlify(buf[0:4]) + " " + binascii.hexlify(buf[4:]))
        self.s_.send(buf)

    def recv(self, size):
        self.print_dbg("Waiting for " + str(size) + " bytes")

        rx = self.s_.recv(size)
        while len(rx) < size:
            # check whether the very front of the data stream contains a failure
            (processed, resp) = self.extract_resp(rx)
            if not resp.io_result.success:
                return rx

            rx += self.s_.recv(size - len(rx))
        return rx

    def extract_buf(self, buf):
        self.print_dbg("data: " + binascii.hexlify(buf[0:4]) + " " + binascii.hexlify(buf[4:]))
        hdr = struct.unpack('i', buf[0:4])[0]

        size = hdr & 0x1fffff
        self.print_dbg("header: type=" + str((hdr >> 21) & 31) + " msg_size=" + str(size) + \
                           " (from " + str(len(buf)) + " total)")

        return (4, size, buf[4:4 + size])

    def extract_hello(self, buf):
        (hsize, msize, msg) = self.extract_buf(buf)

        resp = block_pb2.ServerHello()
        resp.ParseFromString(msg)
        return resp

    def extract_resp(self, buf):
        (hsize, msize, msg) = self.extract_buf(buf)

        resp = block_pb2.Response()
        resp.ParseFromString(msg)
        return (hsize + msize, resp)

    def print_dbg(self, msg):
        if self.debug_:
            print(msg)


def invoke_cli(host, commands, rport):
    c = Connection(False)
    try:
        c.connect(host, rport)
        rv = c.invoke(commands)
        if not rv["success"]:
            logger.info("CLI command failed: " + rv["error_message"])
            logger.info("\tcommand: " + str(commands))
            return None
    except socket_error as e:
        #log("CLI command failed due to a socker error: " + str(e))
        #log("\tcommand: " + str(commands))
        return None

    return rv

# Verify controller status
def controller_status(cport, controller):
    rval = invoke_cli(controller, ["controller-status"], cport)
    logger.info(rval)
    logger.info\
        ('Controller status is: ' + str(rval["controller-status"]))