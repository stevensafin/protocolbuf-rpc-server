import socket
import os
import sys
path = os.path.dirname(os.path.abspath(__file__))
dir = os.path.split(path)[0]
sys.path.append(os.path.join(dir,'status'))

from server_status import ServerStatus
from protocol import RPCProtocol
import status_pb2
import rpc_pb2
import binascii
import timeit

def get_request():
    input = rpc_pb2.Request()
    service = ServerStatus()
    input.service_name = service.GetDescriptor().full_name
    input.method_name = 'RPCStatus'
    data = status_pb2.TCPRequest()
    data.client_ip = 'Zach'
    data.user_name = 'Zach'
    data.user_pass = 'Zach'
    input.request_proto = data.SerializeToString()
    request = input.SerializeToString();
    #print binascii.hexlify(request)
    protocol = RPCProtocol()
    return protocol.build_request(request)

def run():
    request = get_request()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
    sock.connect(('localhost', 8080))  
    sock.send(request)  
    recv = sock.recv(6)  
    protocol = RPCProtocol()
    len = protocol.request_len(recv)
    print len
    ret = sock.recv(len)
    response = rpc_pb2.Response()
    response.ParseFromString(ret)
    service_res = status_pb2.RPCResponse()
    service_res.ParseFromString(response.response_proto)
    print service_res.request_total
    print service_res
    sock.close()  


if __name__ == '__main__':
    t = timeit.Timer('run()','from test_status import run')
    print t.timeit(number=1)
