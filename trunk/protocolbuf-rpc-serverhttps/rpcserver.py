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
"""A RPCServer
"""
import logging
from handler import RPCHandler
from tcpserver import TCPServer
from tornado import ioloop
from protocol import RPCProtocol

class RPCServer(object):
    def __init__(self,port,host=''):
        self.handler = RPCHandler(self)
        self.port = port
        self.host = host
        self.tcpserver = None
        self.serviceMap = {}

    def registerService(self, service):
        '''Register an RPC service.'''
        self.serviceMap[service.GetDescriptor().full_name] = service

    def run(self):
        log.info('Running server on port %d' % self.port)
        rpcprotocol = RPCProtocol()
        self.tcpserver = TCPServer(self.handler,rpcprotocol)
        self.tcpserver.bind(self.port, self.host)
        self.tcpserver.start(0)
        ioloop.IOLoop.instance().start()

    def stop(self):
        self.tcpserver.stop()
        ioloop.IOLoop.instance().stop()

if __name__ == '__main__':
    server = RPCServer(8888)
    server.registerServer()
    server.run()
