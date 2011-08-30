#!/usr/bin/env python
#
# Copyright 2011 Xituan
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
"""A non-blocking, single-threaded RPC TCP server
tornado based, use tornado.ioloop, tornado.stream to 
transimit the net data,a request is embody as len\r\nprotocol buf 
"""

#system import
import errno
import logging
import os
import socket
import time
import binascii

#tornado import
from tornado.escape import utf8, native_str, parse_qs_bytes
from tornado import ioloop
from tornado import iostream
from tornado import stack_context
from tornado.util import b, bytes_type

from protocol import ProtocolException
from status import TCPStatus,RPCStatus

try:
    import fcntl
except ImportError:
    if os.name == 'nt':
        from tornado import win32_support as fcntl
    else:
        raise

try:
    import ssl # Python 2.6+
except ImportError:
    ssl = None

try:
    import multiprocessing # Python 2.6+
except ImportError:
    multiprocessing = None

def _cpu_count():
    if multiprocessing is not None:
        try:
            return multiprocessing.cpu_count()
        except NotImplementedError:
            pass
    try:
        return os.sysconf("SC_NPROCESSORS_CONF")
    except ValueError:
        pass
    logging.error("Could not detect number of processors; "
                  "running with one process")
    return 1

class ReadTimeoutCheck(object):
    """
    io timeout check
    """
    _conns = {}
    _timeout = 0.6

    @classmethod
    def set_timeout(cls,timeout):
        if timeout > 0:
            cls._timeout = timeout

    @classmethod
    def add(cls,conn):
        key = conn.stream.socket.fileno()
        logging.debug('add timeout check ' + str(key))
        if not cls._conns.has_key(key):
            cls._conns[key] = [time.time(),conn]

    @classmethod
    def touch(cls,conn):
        key = conn.stream.socket.fileno()
        logging.debug('touch timeout check ' + str(key))
        if cls._conns.has_key(key):
            cls._conns[key][0] = time.time()

    @classmethod
    def delete(cls,conn):
        key = conn.stream.socket.fileno()
        logging.debug('delete timeout check ' + str(key))
        if cls._conns.has_key(key):
            del cls._conns[key]

    @classmethod
    def run(cls):
        logging.debug('read timeout check')
        now = time.time()
        for k in cls._conns.keys():
            v = cls._conns[k]
            if now - v[0] >= cls._timeout:
                v[1]._on_finish(timeout=True)
                del cls._conns[k]
                logging.debug('delete timeout check ' + str(k))


class TCPServer(object):
    """A non-blocking , single-threaded TCP server
    """
    def __init__(self, handler, protocol, io_loop=None, ssl_options=None):
        """Initializes the server with the given request callback.

        If you use pre-forking/start() instead of the listen() method to
        start your server, you should not pass an IOLoop instance to this
        constructor. Each pre-forked child process will create its own
        IOLoop instance after the forking process.
        """
        self.protocol = protocol
        self.handler = handler
        self.io_loop = io_loop
        self.ssl_options = ssl_options
        self._sockets = {}  # fd -> socket object
        self._started = False

    def listen(self, port, address=None):
        """Binds to the given port and starts the server in a single process.

        This method is a shortcut for:

            server.bind(port, address)
            server.start(1)

        """
        self.bind(port, address)
        self.start(1)

    def bind(self, port, address=None, family=socket.AF_UNSPEC):
        """Binds this server to the given port on the given address.

        To start the server, call start(). If you want to run this server
        in a single process, you can call listen() as a shortcut to the
        sequence of bind() and start() calls.

        Address may be either an IP address or hostname.  If it's a hostname,
        the server will listen on all IP addresses associated with the
        name.  Address may be an empty string or None to listen on all
        available interfaces.  Family may be set to either socket.AF_INET
        or socket.AF_INET6 to restrict to ipv4 or ipv6 addresses, otherwise
        both will be used if available.

        This method may be called multiple times prior to start() to listen
        on multiple ports or interfaces.
        """
        logging.debug('in bind')
        if address == "":
            address = None

        for res in socket.getaddrinfo(address, port, family, socket.SOCK_STREAM,
                                      0, socket.AI_PASSIVE | socket.AI_ADDRCONFIG):
            af, socktype, proto, canonname, sockaddr = res
            sock = socket.socket(af, socktype, proto)
            flags = fcntl.fcntl(sock.fileno(), fcntl.F_GETFD)
            flags |= fcntl.FD_CLOEXEC
            fcntl.fcntl(sock.fileno(), fcntl.F_SETFD, flags)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if af == socket.AF_INET6:
                # On linux, ipv6 sockets accept ipv4 too by default,
                # but this makes it impossible to bind to both
                # 0.0.0.0 in ipv4 and :: in ipv6.  On other systems,
                # separate sockets *must* be used to listen for both ipv4
                # and ipv6.  For consistency, always disable ipv4 on our
                # ipv6 sockets and use a separate ipv4 socket when needed.
                #
                # Python 2.x on windows doesn't have IPPROTO_IPV6.
                if hasattr(socket, "IPPROTO_IPV6"):
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)

            sock.setblocking(0)
            sock.bind(sockaddr)
            sock.listen(128)
            self._sockets[sock.fileno()] = sock
            if self._started:
                self.io_loop.add_handler(sock.fileno(), self._handle_events, ioloop.IOLoop.READ)

    def start(self, num_processes=1):
        """Starts this server in the IOLoop.

        By default, we run the server in this process and do not fork any
        additional child process.

        If num_processes is None or <= 0, we detect the number of cores
        available on this machine and fork that number of child
        processes. If num_processes is given and > 1, we fork that
        specific number of sub-processes.

        Since we use processes and not threads, there is no shared memory
        between any server code.

        Note that multiple processes are not compatible with the autoreload
        module (or the debug=True option to tornado.web.Application).
        When using multiple processes, no IOLoops can be created or
        referenced until after the call to HTTPServer.start(n).
        """
        logging.debug('in start')
        assert not self._started
        self._started = True
        if num_processes is None or num_processes <= 0:
            num_processes = _cpu_count()

        if num_processes > 1 and ioloop.IOLoop.initialized():
            logging.error("Cannot run in multiple processes: IOLoop instance "
                          "has already been initialized. You cannot call "
                          "IOLoop.instance() before calling start()")
            num_processes = 1

        if num_processes > 1:
            logging.info("Pre-forking %d server processes", num_processes)
            for i in range(num_processes):
                if os.fork() == 0:
                    import random
                    from binascii import hexlify
                    try:
                        # If available, use the same method as
                        # random.py
                        seed = long(hexlify(os.urandom(16)), 16)
                    except NotImplementedError:
                        # Include the pid to avoid initializing two
                        # processes to the same value
                        seed(int(time.time() * 1000) ^ os.getpid())

                    random.seed(seed)
                    self.io_loop = ioloop.IOLoop.instance()
                    for fd in self._sockets.keys():
                        self.io_loop.add_handler(fd, self._handle_events,
                                                 ioloop.IOLoop.READ)
                        return
            os.waitpid(-1, 0)
        else:
            if not self.io_loop:
                self.io_loop = ioloop.IOLoop.instance()

            for fd in self._sockets.keys():
                self.io_loop.add_handler(fd, self._handle_events,
                                         ioloop.IOLoop.READ)
        check = ioloop.PeriodicCallback(ReadTimeoutCheck.run,ReadTimeoutCheck._timeout * 1000)
        check.start()

    def stop(self):
        """Stops listening for new connections.

        Requests currently in progress may still continue after the
        server is stopped.
        """
        for fd, sock in self._sockets.iteritems():
            self.io_loop.remove_handler(fd)
            sock.close()

    def _handle_events(self, fd, events):
        logging.debug('in handle events')
        while True:
            try:
                connection, address = self._sockets[fd].accept()
            except socket.error, e:
                if e.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    return
                raise
            if self.ssl_options is not None:
                assert ssl, "Python 2.6+ and OpenSSL required for SSL"
                try:
                    connection = ssl.wrap_socket(connection,
                                                 server_side=True,
                                                 do_handshake_on_connect=False,
                                                 **self.ssl_options)
                except ssl.SSLError, err:
                    if err.args[0] == ssl.SSL_ERROR_EOF:
                        return connection.close()
                    else:
                        raise
                except socket.error, err:
                    if err.args[0] == errno.ECONNABORTED:
                        return connection.close()
                    else:
                        raise
            try:
                if self.ssl_options is not None:
                    stream = iostream.SSLIOStream(connection, io_loop=self.io_loop)
                else:
                    stream = iostream.IOStream(connection, io_loop=self.io_loop)
                    TCPConnection(stream, address, self.protocol,self.handler)
            except:
                logging.error("Error in connection callback", exc_info=True)

class _BadRequestException(Exception):
    """Exception class for malformed requests."""
    pass


class TCPConnection(object):
    """Handles a connection to an TCP client, executing requests.
    """
    def __init__(self, stream, address, protocol,handler):
        logging.debug('a new connection')
        self.stream = stream
        self.address = address
        self.protocol = protocol
        self.handler = handler
        self._request_finished = False
        # Save stack context here, outside of any request.  This keeps
        # contexts from one request from leaking into the next.
        self._header_callback = stack_context.wrap(self._on_request_len)
        TCPStatus.start_request(self.stream.socket.fileno())
        if protocol.is_delimiter():
            logging.debug('read_until ' + b(protocol.header_delimiter()))
            self.stream.read_until(b(protocol.header_delimiter()), self._header_callback)
            ReadTimeoutCheck.add(self)
        else:
            logging.debug('read_bytes ')
            self.stream.read_bytes(protocol.header_length(), self._header_callback)
            ReadTimeoutCheck.add(self)

    def _on_request_len(self,data):
         """
         get a request len, and restruct the len ,get the real request finally
         reconstruct the protocol header
         """
         ReadTimeoutCheck.touch(self)
         logging.debug('in header')
         try:
             content_length = self.protocol.request_len(data)
             if content_length:
                 if content_length > self.stream.max_buffer_size:
                     raise _BadRequestException("Request-Length too long")
                 self.stream.read_bytes(content_length, self._on_request_body)
                 return
             else:
                 raise _BadRequestException("Request-Header %s" % data)
         except ProtocolException, e:
             logging.error("Malformed RPC request from %s: %s",
                           self.address[0], e)
             self.stream.close()

    def _on_request_body(self, data):
        ReadTimeoutCheck.delete(self)
        logging.debug('in body')
        try:
            response = self.handler.handle(data)
            response = self.protocol.build_response(response)
            logging.debug('resp ' + binascii.hexlify(response))
            self.stream.write(response,self._on_finish)
        except Exception,e:
            logging.error("Error Request RPC request from %s: %s %s",
                          self.address[0], data,e)
            return

    def _on_finish(self,timeout=False):
        self._request_finished = True
        TCPStatus.end_request(self.stream.socket.fileno(),timeout)
        logging.debug('in finish')
        self.stream.close()
