import pytest
from app.proxy.checker import ProxyChecker


class TestProxyChecker:
    def test_build_proxy_url_without_auth(self):
        checker = ProxyChecker()
        url = checker._build_proxy_url("192.168.1.1", 8080, "http")
        assert url == "http://192.168.1.1:8080"

    def test_build_proxy_url_with_auth(self):
        checker = ProxyChecker()
        url = checker._build_proxy_url("192.168.1.1", 8080, "http", "user", "pass")
        assert url == "http://user:pass@192.168.1.1:8080"

    def test_build_proxy_url_https(self):
        checker = ProxyChecker()
        url = checker._build_proxy_url("proxy.example.com", 443, "https")
        assert url == "https://proxy.example.com:443"

    def test_build_proxy_url_socks5(self):
        checker = ProxyChecker()
        url = checker._build_proxy_url("10.0.0.1", 1080, "socks5")
        assert url == "socks5://10.0.0.1:1080"
