#!/usr/bin/python

import block_pb2
import sys, socket, struct, binascii
from optparse import OptionParser, OptionGroup

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

def parse_command_line(cmd_options):
    usage = '''Usage: %prog -a <destination address> <command>

Commands:
  capabilities, replicas, status, replication-status

  connect <host> <port>
  replicas
  
  controller-status

  snap <name>
  list-snapshots
  changed-blocks <snap-name>
  
  rebuild <host> <port>
  replication-status

  dump-volume -f <file name>
  load-volume -f <file name>'''

    parser = OptionParser(usage=usage)

    # global things
    parser.add_option("-d", "--debug", action="store_true", default=False)
    parser.add_option("-f", "--file-name", dest="filename")
    parser.add_option("-z", "--size", type="int", dest="size",
                      help="size of the volume dump/load (in bytes)")
    parser.add_option("-o", "--offset", type="int", dest="offset",
                      help="offset of the volume dump/load (in bytes)")
    parser.add_option("-s", "--snapshot", dest="snap")
    parser.add_option("-x", "--xml", action="store_true", default=False)

    # storage things
    sgroup = OptionGroup(parser,
                         "Connection options",
                         "these define addresses, ports, etc needed for connectivity")
    sgroup.add_option("-a", "--address", action="store", type="string",
                      help="The IP address (or host) to connect to")
    sgroup.add_option("-p", "--port", action="store", type="int", default=4000,
                      help="destination port (default=4000)")
    parser.add_option_group(sgroup)

    (opt, args) = parser.parse_args(cmd_options)
    if len(args) == 0:
        parser.error("Need a <command> at the end of the command line!")

    return (opt, args)
                        
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
        
        self.print_dbg("Connecting to " + address + ":" + str(port) + "...")
        self.s_.connect((address, port))

        # Start with the Hello
        req = block_pb2.ClientHello()
        req.version = 1
        self.print_dbg("Sending Hello")
        self.send(compose_buf(req.SerializeToString()))
        rx = self.s_.recv(1024)
        self.print_dbg("Received " + str(len(rx)) + " bytes of data")
        resp = self.extract_hello(rx)
        self.print_dbg("Connected to replica v=" + str(resp.version))
        self.connected_ = True
        
    def invoke(self, terms):
        # prepare the request
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
                                                            
if __name__ == "__main__":
    (options, terms) = parse_command_line(sys.argv[1:])
    c = Connection(options.debug)
    c.connect(options.address, options.port)

    # Handle file operations separately, as this requires explicit invoke_xxxx() calls and
    # extra arguments
    if terms[0] == "dump-volume":
        if not options.filename:
            sys.exit("Please provide the output file name")
        c.invoke_read(options.filename, snap = options.snap,
                      offset = options.offset, size = options.size)
        sys.exit(0)
    if terms[0] == "load-volume":
        if not options.filename:
            sys.exit("Please provide the input file name")
        c.invoke_write(options.filename,
                      offset = options.offset, size = options.size)
        sys.exit(0)


    # Handle the basic management calls
    rv = c.invoke(terms)

    if terms[0] == "capabilities":
        print("Got Capabilities:" +
              "\n  id:\t\t" + rv["id"] +
              "\n  replica capacity:\t" + str(rv["replica_capacity"]) +
              "\n  replica usage:\t" + str(rv["replica_usage"]) +
              "\n  volume size:\t" + str(rv["volume_size"]) +
              "\n  block size:\t" + str(rv["block_size"]))
    elif terms[0] == "status":
        print("Got Status:\n  online: " + str(rv["online"]))
    elif terms[0] == "snap" or terms[0] == "connect":
        print("Got Status:\n  success: " + str(rv["success"]))
        if not rv["success"]:
            print("  error: " + rv["error_message"])
    elif terms[0] == "remove-snap":
        print("Got Status:\n  success: " + str(rv["success"]))
        if not rv["success"]:
            print("  error: " + rv["error_message"])
    elif terms[0] == "list-snapshots":
        print("Got snapshots:")
        for s in rv:
            print("  [" + str(s["id"]) + "] " + s["name"])
    elif terms[0] == "changed-blocks":
        print("Got a list:\n")
        if options.xml:
            print('<?xml version="1.0" encoding="ISO-8859-1"?>')
            print('<change-set>')
        for (off, size) in rv:
            if options.xml:
                print('  <range offset="' + str(off) + '" size="' + str(size) + '"/>')
            else:
                print(str(off) + ":" + str(size))
        if options.xml:
            print('</change-set>')
    elif terms[0] == "replication-status":
        print("Got status:")
        print("  status: " + block_pb2.Response.ReplicationInfo.Status.Name(rv["status"]))
    elif terms[0] == "replicas":
        print("Got Replica info:")
        for (host, port, status) in rv["replicas"]:
            print("\t" + host + ":" + str(port) + "\t " + status)
    elif terms[0] == "controller-status":
        print("Got controller status: "+ str(rv["controller-status"]))
    else:
        print("Unrecognized response: " + str(rv))
