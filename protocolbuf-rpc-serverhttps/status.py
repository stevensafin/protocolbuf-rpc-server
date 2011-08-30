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
"""
get the server run status
"""
import time
import logging

class RPCStatus(object):
    _status = {'request_total':0,'bad_request':0,'service_not_found':{},'method_not_found':{},'service':{}}
    _request = {}

    @classmethod
    def start_request(cls,id):
        if not id in cls._request:
            cls._request[id] = float(id)
        cls._status['request_total'] += 1
        #cls._status['request'] += 1

    @classmethod
    def end_request(cls,service_name,method_name,id):
        logging.debug(id)
        if not id in cls._request:
            logging.debug(id + ' not in request')
            pass
        now = time.time()
        dur = now - cls._request[id]
        key = '.'.join([service_name,method_name])
        if not key in cls._status['service']:
            cls._status['service'][key] = {'min_time':dur,'max_time':dur,'avg_time':dur,'request_total':1}
        else:
            short = cls._status['service'][key]
            if short['min_time'] > dur:
                short['min_time'] = dur
            if short['max_time'] < dur:
                short['max_time'] = dur
            short['request_total'] += 1
            short['avg_time'] = short['avg_time'] * (short['request_total'] -1) /short['request_total'] + dur/short['request_total']
        del cls._request[id]


    @classmethod
    def bad_request(cls,id):
        cls._status['bad_request'] += 1
        if cls._request.has_key(id):
            del cls._request[id]

    @classmethod
    def service_not_found(cls,service_name,id):
        if not cls._status['service_not_found'].has_key(service_name):
            cls.status['service_not_found'][service_name] = 1
        else:
            cls.status['service_not_found'][service_name] += 1
        if cls._request.has_key(id):
            del cls._request[id]

    @classmethod
    def method_not_found(cls,service_name,method_name,id):
        key = '.'.join([service_name,method_name])
        if not key in cls._status['method_not_found']:
            cls.status['method_not_found'][key] = 1
        else:
            cls.status['method_not_found'][key] += 1
        if cls._request.has_key(id):
            del cls._request[id]

    @classmethod
    def run(cls):
        service_not_found = ','.join("%s=%d" % i for i in cls._status['service_not_found'].iteritems())
        service_not_found = service_not_found or '0'
        method_not_found = ','.join("%s=%d" % i for i in cls._status['method_not_found'].iteritems())
        method_not_found = method_not_found or '0'
        service = ','.join("%s=%d" % i for i in cls._status['service'].iteritems())
        service = service or '0'
        value = "request_total %d bad_request %d service_not_found %s method_not_found %s service %s" % (cls._status['request_total'],cls._status['bad_request'],service_not_found,method_not_found,service)
        logging.debug(value)

class TCPStatus(object):
    _status = {'request_total':0,'read_timeout':0,'max_request_time':0,'min_request_time':999,'avg_request_time':0}
    _socks = {}

    @classmethod
    def start_request(cls,id):
        """
        one request start
        """
        cls._status['request_total'] += 1
        cls._socks[id] = time.time()

    @classmethod
    def end_request(cls,id,timeout):
        """
        one request end
        """
        try:
            now = time.time()
            dur = now - cls._socks[id]
            logging.debug(dur)
            if cls._status['max_request_time'] < dur:
                cls._status['max_request_time'] = dur

            if cls._status['min_request_time'] > dur:
                cls._status['min_request_time'] = dur

            if timeout:
                cls._status['read_timeout'] += 1

            total = cls._status['request_total']
            cls._status['avg_request_time'] = cls._status['avg_request_time'] * (total - 1) /total + dur/total
            del cls._socks[id]
        except Exception,e:
            logging.debug(e)


    @classmethod
    def run(cls):
        """
        every interval flush the status to log file
        """
        value = "request_total %d read_timeout %d request %d max_request_time %.6f min_request_time %.6f avg_request_time %.6f" % (cls._status['request_total'],cls._status['read_timeout'],cls._status['request'],cls._status['max_request_time'],cls._status['min_request_time'],cls._status['avg_request_time'])
        logging.debug(value)
