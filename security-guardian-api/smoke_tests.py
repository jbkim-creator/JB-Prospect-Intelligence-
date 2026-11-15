"""Offline safety and input-validation smoke tests. No external DNS or HTTP requests."""
import ipaddress
import io
import socket
import unittest
from unittest.mock import patch

PUBLIC = ("93.184.216.34",)

def run(app):
    class Smoke(unittest.TestCase):
        def fake(self, addresses):
            return [(socket.AF_INET6 if ":" in a else socket.AF_INET, socket.SOCK_STREAM, 6, "", (a,443)) for a in addresses]

        def test_accept_public(self):
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(PUBLIC)):
                self.assertEqual(app.inspect_host("example.com"), list(PUBLIC))
        def test_accept_subdomain(self):
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(PUBLIC)):
                self.assertEqual(app.inspect_host("www.example.com"), list(PUBLIC))
        def test_reject_empty(self):
            with self.assertRaises(ValueError):app.inspect_host("")
        def test_reject_localhost(self):
            with self.assertRaises(ValueError):app.inspect_host("server.localhost")
        def test_reject_private_ipv4(self):
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(["192.168.1.5"])):
                with self.assertRaises(ValueError):app.inspect_host("example.com")
        def test_reject_loopback_ipv4(self):
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(["127.0.0.1"])):
                with self.assertRaises(ValueError):app.inspect_host("example.com")
        def test_reject_private_ipv6(self):
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(["fd00::1"])):
                with self.assertRaises(ValueError):app.inspect_host("example.com")
        def test_reject_mixed_addresses(self):
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(["93.184.216.34","10.0.0.3"])):
                with self.assertRaises(ValueError):app.inspect_host("example.com")
        def test_reject_unsupported_host(self):
            with self.assertRaises(ValueError):app.inspect_host("a.invalid")
        def test_reject_missing_dns(self):
            with patch.object(app.socket, "getaddrinfo", return_value=[]):
                with self.assertRaises(ValueError):app.inspect_host("example.com")
        def test_reject_excess_addresses(self):
            ips = ["8.8.%d.%d" % (i//256,i%256) for i in range(21)]
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(ips)):
                with self.assertRaises(ValueError):app.inspect_host("example.com")
        def test_prefer_ipv4(self):
            with patch.object(app.socket, "getaddrinfo", return_value=self.fake(["2606:4700:4700::1111","1.1.1.1"])):
                self.assertEqual(app.inspect_host("example.com")[0],"1.1.1.1")

    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Smoke)
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=1).run(suite)
    print("JBRO SMOKE TESTS:", result.testsRun, "executed,", "PASS" if result.wasSuccessful() else "FAIL", flush=True)
    if not result.wasSuccessful():
        print(output.getvalue(),flush=True)
        raise RuntimeError("Preflight smoke tests failed")
