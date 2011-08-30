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
import struct
import logging

class Protocol(object):
    """
    net protocol
    """
    def validate_header(self,header):
        pass

    def header_delimiter(self):
        pass

    def header_length(self):
        pass

    def is_delimiter(self):
        pass

    def build_response(self,data):
        pass

class ProtocolException(Exception):
    pass

class RPCProtocol(Protocol):
    """
    RPC Protocol
    """
    def is_delimiter(self):
        return True

    def header_delimiter(self):
        return "\r\n"

    def build_response(self,data):
        header = self.build_header(len(data))
        return header+"\r\n"+data

    def build_request(self,data):
        header = self.build_header(len(data))
        return header+"\r\n"+data

    def request_len(self,header):
        logging.debug(header)
        end = header.find("\r\n")
        if end == -1:
            raise ProtocolException("header len error,delimiter not find")
        try:
            len = struct.unpack("!I",header[:end])[0]
        except struct.error:
            raise ProtocolException("header format error")
        return len

    def build_header(self,len):
        return struct.pack("!I",len)


