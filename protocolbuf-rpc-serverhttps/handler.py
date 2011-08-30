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
"""A handler, recv the data,finish the request ,return the response
"""
import logging
import rpc_pb2 as rpc_pb
from controller import SocketRpcController 
from status import RPCStatus
import error
import time

class Callback():
    '''Class to allow execution of client-supplied callbacks.'''

    def __init__(self):
        self.invoked = False
        self.response = None

    def run(self, response):
        self.response = response
        self.invoked = True

class Handler(object):
    """ Handler abstract class
    """
    def handle():
        raise Exception("not implement yet")

class RPCHandler(Handler):
    """RPC Handler
    """
    def __init__(self,rpc_server):
        self.rpc_server = rpc_server

    def handle(self,recv):
        # Evaluate and execute the request
        rpcResponse = self.validateAndExecuteRequest(recv)
        logging.debug("Response to return to client \n %s" % rpcResponse)
        return rpcResponse.SerializeToString()

    def validateAndExecuteRequest(self, input):
        '''Match a client request to the corresponding service and method on
        the server, and then call the service.'''

        # Parse and validate the client's request
        self.id = "%f" % time.time()
        RPCStatus.start_request(self.id)
        try:
            request = self.parseServiceRequest(input)
        except error.BadRequestDataError, e:
            RPCStatus.bad_request(self.id)
            return self.handleError(e)

        # Retrieve the requested service
        try:
            service = self.retrieveService(request.service_name)
        except error.ServiceNotFoundError, e:
            RPCStatus.service_not_found(request.service_name,self.id)
            return self.handleError(e)

        # Retrieve the requested method
        try:
            method = self.retrieveMethod(service, request.method_name)
        except error.MethodNotFoundError, e:
            RPCStatus.method_not_found(request.service_name,request.method_name,self.id)
            return self.handleError(e)

        # Retrieve the protocol message
        try:
            proto_request = self.retrieveProtoRequest(service, method, request)
        except error.BadRequestProtoError, e:
            return self.handleError(e)

        # Execute the specified method of the service with the requested params
        try:
            response = self.callMethod(service, method, proto_request)
            RPCStatus.end_request(request.service_name,request.method_name,self.id)
        except error.RpcError, e:
            return self.handleError(e)

        return response

    def parseServiceRequest(self, bytestream_from_client):
        '''Validate the data stream received from the client.'''

        # Convert the client request into a PB Request object
        request = rpc_pb.Request()

        # Catch anything which isn't a valid PB bytestream
        try:
            request.MergeFromString(bytestream_from_client)
        except Exception, e:
            raise error.BadRequestDataError("Invalid request from \
                                            client (decodeError): " + str(e))

        # Check the request is correctly initialized
        if not request.IsInitialized():
            raise error.BadRequestDataError("Client request is missing \
                                             mandatory fields")
        logging.debug('Request = %s' % request)

        return request

    def retrieveService(self, service_name):
        '''Match the service request to a registered service.'''
        logging.debug('request service: ' + service_name)
        service = self.rpc_server.serviceMap.get(service_name)
        if service is None:
            msg = "Could not find service '%s'" % service_name
            raise error.ServiceNotFoundError(msg)

        return service

    def retrieveMethod(self, service, method_name):
        '''Match the method request to a method of a registered service.'''
        logging.debug('request method: ' + method_name)
        method = service.DESCRIPTOR.FindMethodByName(method_name)
        if method is None:
            msg = "Could not find method '%s' in service '%s'"\
                   % (method_name, service.DESCRIPTOR.name)
            raise error.MethodNotFoundError(msg)

        return method

    def retrieveProtoRequest(self, service, method, request):
        ''' Retrieve the users protocol message from the RPC message'''
        proto_request = service.GetRequestClass(method)()
        try:
            proto_request.ParseFromString(request.request_proto)
        except Exception, e:
            raise error.BadRequestProtoError(unicode(e))

        # Check the request parsed correctly
        if not proto_request.IsInitialized():
            raise error.BadRequestProtoError('Invalid protocol request \
                                              from client')

        return proto_request

    def callMethod(self, service, method, proto_request):
        '''Execute a service method request.'''
        logging.debug('Calling service %s' % service)
        logging.debug('Calling method %s' % method)

        # Create the controller (initialised to success) and callback
        controller = SocketRpcController()
        callback = Callback()
        try:
            service.CallMethod(method, controller, proto_request, callback)
        except Exception, e:
            raise error.RpcError(unicode(e))

        # Return an RPC response, with payload defined in the callback
        response = rpc_pb.Response()
        if callback.response:
            response.callback = True
            response.response_proto = callback.response.SerializeToString()
        else:
            response.callback = callback.invoked

        # Check to see if controller has been set to not success by user.
        if controller.failed():
            response.error = controller.error()
            response.error_reason = rpc_pb.RPC_FAILED

        return response

    def handleError(self, e):
        '''Produce an RPC response to convey a server error to the client.'''
        msg = "%d : %s" % (e.rpc_error_code, e.message)
        logging.error(msg)

        # Create error reply
        response = rpc_pb.Response()
        response.error_reason = e.rpc_error_code
        response.error = e.message
        return response
