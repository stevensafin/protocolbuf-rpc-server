import sys
sys.path.append('..')

import unittest
import protocol
import struct
import binascii

class TestRPCProtocol(unittest.TestCase):

    def setUp(self):
        self.pro = protocol.RPCProtocol()

    def test_build_response(self):
        data = 'sss'
        res = self.pro.build_response(data)
        print binascii.hexlify(res)

    def test_build_header(self):
        pack = struct.pack("!I",80)
        self.assertEqual(self.pro.build_header(80),pack)


    def test_request_len(self):
        header = struct.pack("!I",80) + '\r\n';
        self.assertEqual(self.pro.request_len(header),80)
        #with self.assertRaises(protocol.ProtocolException, self.pro.request_len('sss')) as pe:
        #    print pe


if __name__ == '__main__':
        unittest.main()
