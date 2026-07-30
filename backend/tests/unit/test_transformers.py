from dataforge.backend.app.extraction.transformers import DataTransformer


class TestDataTransformer:
    def test_to_json(self):
        data = {"name": "test", "value": 123}
        result = DataTransformer.to_json(data)
        assert isinstance(result, str)
        assert '"name"' in result
        assert '"test"' in result

    def test_to_json_pretty(self):
        data = {"name": "test"}
        result = DataTransformer.to_json(data, pretty=True)
        assert "\n" in result

    def test_to_csv_basic(self):
        data = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        result = DataTransformer.to_csv(data)
        assert "name,age" in result
        assert "Alice" in result
        assert "Bob" in result

    def test_to_csv_empty(self):
        result = DataTransformer.to_csv([])
        assert result == ""

    def test_flatten_json(self):
        data = {"person": {"name": "Alice", "address": {"city": "NYC"}}}
        result = DataTransformer.flatten_json(data)
        assert result["person_name"] == "Alice"
        assert result["person_address_city"] == "NYC"

    def test_clean_html_removes_scripts(self):
        html = "<html><script>alert('x')</script><body><p>Hello</p></body></html>"
        result = DataTransformer.clean_html_content(html)
        assert "script" not in result
        assert "Hello" in result

    def test_extract_urls(self):
        text = "Visit https://example.com and http://test.com/path"
        urls = DataTransformer.extract_urls(text)
        assert "https://example.com" in urls
        assert "http://test.com/path" in urls

    def test_extract_emails(self):
        text = "Contact us at hello@example.com or support@test.org"
        emails = DataTransformer.extract_emails(text)
        assert "hello@example.com" in emails
        assert "support@test.org" in emails

    def test_truncate_text(self):
        text = "A" * 1000
        result = DataTransformer.truncate_text(text, max_chars=100)
        assert len(result) <= 150
        assert "truncated" in result
