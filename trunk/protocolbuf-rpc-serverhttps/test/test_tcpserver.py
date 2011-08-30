import sys
sys.path.append('..')
sys.path.append('../examples/helloworld')
sys.path.append('../examples/user')
sys.path.append('../status')

import handler
import logging
import rpcserver
from tcpserver import TCPServer
from protocol import RPCProtocol
from HelloWorldServiceImpl import HelloWorldImpl
from user_service import UserServiceImpl
from tornado import ioloop
from server_status import ServerStatus

class TestTCPServer:
    def __init__(self):
        self.server = rpcserver.RPCServer(8080)
        self.server.registerService(HelloWorldImpl())
        self.server.registerService(ServerStatus())
        self.server.registerService(UserServiceImpl())
        self.handler = handler.RPCHandler(self.server)
        self.tcpserver = TCPServer(self.handler,RPCProtocol())

    def run(self):
        logging.getLogger().setLevel(logging.DEBUG)
        self.tcpserver.bind(8080)
        self.tcpserver.start(0)
        ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    server = TestTCPServer()
    server.run()
