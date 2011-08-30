#!/usr/bin/python
# Copyright (c) 2009 Las Cumbres Observatory (www.lcogt.net)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

'''user.py - 'User Login' service implementation example.
give a db 
May 2009
'''

import user_pb2
import time
import hashlib
import logging
from tornado.database import Connection,Row


class UserServiceImpl(user_pb2.UserService):
    def enc_pass(self,passwd):
        token = '@4!@#$%@'
        return hashlib.md5(passwd+token).hexdigest()

    def UserLogin(self, controller, request, done):
        #print request

        # Extract name from the message received
        name = request.user_name
        passwd = self.enc_pass(request.user_pass)
        ret = False
        db = Connection('localhost','xituan-thinkphp','root')
        try:
            query = "select count(*) as cnt from user_login where `user_email` = '%s' and `user_password` = '%s'" % (name,passwd)
            logging.debug(query)
            ret = db.get(query)
        except Exception,e:
            logging.error(e)
        finally:
            del db

        # Create a reply
        response = user_pb2.UserLoginResponse()
        response.login = bool(ret.cnt)

        # We're done, call the run method of the done callback
        done.run(response)
