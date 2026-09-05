"""Permanente Tests fuer den Update-Mechanismus (offline-sicher + Banner)."""
import os
import sys
import json
import unittest
import http.server
import threading
import socketserver

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from devispro import version as ver
from devispro import updates as upd


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


class TestVersion(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(ver.parse("1.2.3"), (1, 2, 3))
        self.assertEqual(ver.parse("v1.2"), (1, 2, 0))
        self.assertEqual(ver.parse("2"), (2, 0, 0))

    def test_newer(self):
        self.assertTrue(ver.newer("1.0.1", "1.0.0"))
        self.assertTrue(ver.newer("1.1.0", "1.0.9"))
        self.assertFalse(ver.newer("1.0.0", "1.0.0"))
        self.assertFalse(ver.newer("0.9.0", "1.0.0"))


class TestUpdateCheck(unittest.TestCase):
    def _serve(self, payload):
        payload_bytes = json.dumps(payload).encode("utf-8")

        class H(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload_bytes)))
                self.end_headers()
                self.wfile.write(payload_bytes)

            def log_message(self, *a):
                pass

        httpd = socketserver.TCPServer(("127.0.0.1", 0), H)
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        return f"http://127.0.0.1:{port}/version.json", httpd

    def test_available_newer(self):
        url, httpd = self._serve({
            "version": "9.9.9", "channel": "stable",
            "download_url": "https://devispro.ch",
            "notes": {"de": ["Fehler behoben", "Neue Funktion X"]},
        })
        try:
            res = upd.check(force=True, url=url)
            self.assertTrue(res["available"])
            self.assertEqual(res["latest"], "9.9.9")
            banner = upd.render_banner(res, "de")
            self.assertIn("Update verfügbar", banner)
            self.assertIn("Fehlerbehebungen", banner)
            self.assertIn("Neue Funktion X", banner)
        finally:
            httpd.shutdown()

    def test_no_update_equal(self):
        url, httpd = self._serve({
            "version": ver.VERSION, "notes": {"de": ["nix"]},
        })
        try:
            res = upd.check(force=True, url=url)
            self.assertFalse(res["available"])
            self.assertEqual(upd.render_banner(res, "de"), "")
        finally:
            httpd.shutdown()

    def test_offline_graceful(self):
        # nicht erreichbare URL -> kein Absturz, available=False
        res = upd.check(force=True, url="http://127.0.0.1:1/version.json")
        self.assertFalse(res["available"])
        self.assertIn("local", res)
        self.assertIn("latest", res)


if __name__ == "__main__":
    unittest.main(verbosity=2)
