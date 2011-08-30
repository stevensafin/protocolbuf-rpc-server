import sys
sys.path.append('..')
sys.path.append('../examples/helloworld')

import unittest
import handler
import rpcserver
from protocol import RPCProtocol
from HelloWorldServiceImpl import HelloWorldImpl
import hello_world_pb2
import rpc_pb2

class TestRPCHandler(unittest.TestCase):

    def setUp(self):
        self.server = rpcserver.RPCServer(8888)
        self.service = HelloWorldImpl()
        self.server.registerService(self.service)
        self.handler = handler.RPCHandler(self.server)

    def test_handle(self):
        input = rpc_pb2.Request()
        input.service_name = self.service.GetDescriptor().full_name
        input.method_name = 'HelloWorld'
        data = hello_world_pb2.HelloRequest()
        data.my_name = 'Zach'
        input.request_proto = data.SerializeToString()
        ret = self.handler.handle(input.SerializeToString())
        response = rpc_pb2.Response()
        response.ParseFromString(ret)
        service_res = hello_world_pb2.HelloResponse()
        service_res.ParseFromString(response.response_proto)
        self.assertEqual(service_res.hello_world ,'Hello Zach')

if __name__ == '__main__':
        unittest.main()
