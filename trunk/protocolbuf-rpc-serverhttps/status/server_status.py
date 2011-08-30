import os
import sys
path = os.path.dirname(os.path.abspath(__file__))
dir = os.path.split(path)[0]
sys.path.append(dir)

import status_pb2 
import logging
import status

class ServerStatus(status_pb2.StatusService):
    def TCPStatus(self,controller,request,done):
        logging.debug(request)
        response = status_pb2.TCPResponse()
        logging.debug(status.TCPStatus._status)
        response.request_total = status.TCPStatus._status['request_total']
        response.read_timeout = status.TCPStatus._status['read_timeout']
        response.max_request_time = status.TCPStatus._status['max_request_time']
        response.min_request_time = status.TCPStatus._status['min_request_time']
        response.avg_request_time = status.TCPStatus._status['avg_request_time']
        done.run(response)

    def RPCStatus(self,controller,request,done):
        logging.debug(request)
        response = status_pb2.RPCResponse()
        stat = status.RPCStatus._status
        response.request_total = stat['request_total']
        response.bad_request = stat['bad_request']
        for name,v in stat['service_not_found'].iteritems():
            response.service_not_found.add(service_name = name,count = v)
        for name,v in stat['method_not_found'].iteritems():
            response.method_not_found.add(method_name = name,count = v)
        for name,v in stat['service'].iteritems():
            response.service_status.add(service_name = name,min_time = v['min_time'],max_time=v['max_time'],avg_time=v['avg_time'],request_total=v['request_total'])
        done.run(response)

