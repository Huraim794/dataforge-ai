from app.proxy.rotator import ProxyRotator


class TestProxyRotator:
    def setup_method(self):
        self.proxies = [
            {
                "id": "1",
                "host": "192.168.1.1",
                "port": 8080,
                "weight": 1.0,
                "country": "US",
            },
            {
                "id": "2",
                "host": "192.168.1.2",
                "port": 8080,
                "weight": 2.0,
                "country": "GB",
            },
            {
                "id": "3",
                "host": "192.168.1.3",
                "port": 8080,
                "weight": 0.5,
                "country": "DE",
            },
        ]

    def test_get_next_cycles_through_proxies(self):
        rotator = ProxyRotator(self.proxies)
        first = rotator.get_next()
        second = rotator.get_next()
        third = rotator.get_next()
        fourth = rotator.get_next()
        assert first == self.proxies[0]
        assert second == self.proxies[1]
        assert third == self.proxies[2]
        assert fourth == self.proxies[0]

    def test_get_random_returns_proxy(self):
        rotator = ProxyRotator(self.proxies)
        proxy = rotator.get_random()
        assert proxy in self.proxies

    def test_get_weighted_returns_proxy(self):
        rotator = ProxyRotator(self.proxies)
        proxy = rotator.get_weighted()
        assert proxy in self.proxies

    def test_get_by_country_finds_match(self):
        rotator = ProxyRotator(self.proxies)
        proxy = rotator.get_by_country("US")
        assert proxy is not None
        assert proxy["country"] == "US"

    def test_get_by_country_no_match(self):
        rotator = ProxyRotator(self.proxies)
        proxy = rotator.get_by_country("JP")
        assert proxy is None

    def test_empty_proxies(self):
        rotator = ProxyRotator([])
        assert rotator.get_next() is None
        assert rotator.get_random() is None
        assert rotator.get_weighted() is None

    def test_update_proxies(self):
        rotator = ProxyRotator(self.proxies)
        new_proxies = [{"id": "4", "host": "10.0.0.1", "port": 3128}]
        rotator.update_proxies(new_proxies)
        proxy = rotator.get_next()
        assert proxy["id"] == "4"
