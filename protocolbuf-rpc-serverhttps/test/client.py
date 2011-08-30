import socket
import sys
sys.path.append('..')
sys.path.append('../examples/user')

from user_service import UserServiceImpl
from protocol import RPCProtocol
import user_pb2
import rpc_pb2
import binascii
import timeit

def get_request():
    input = rpc_pb2.Request()
    service = UserServiceImpl()
    input.service_name = service.GetDescriptor().full_name
    input.method_name = 'UserLogin'
    data = user_pb2.UserLoginRequest()
    data.user_name = 'linchg@gmail.com'
    data.user_pass = 'xituan'
    input.request_proto = data.SerializeToString()
    request = input.SerializeToString();
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
    service_res = user_pb2.UserLoginResponse()
    service_res.ParseFromString(response.response_proto)
    print service_res.login
    sock.close()  


if __name__ == '__main__':
    t = timeit.Timer('run()','from client import run')
    print t.timeit(number=1)
