import aioresponses
import pytest
from services.api.jisho import JapaneseConnection


@pytest.mark.asyncio
async def test_get_data_returns_formatted_output():
    mock_response = {
        "meta": {"status": 200},
        "data": [{"japanese": [{"word": "猫", "reading": "ねこ"}]}],
    }
    with aioresponses.aioresponses() as mocked:
        mocked.get(
            "https://jisho.org/api/v1/search/words?keyword=cat",
            payload=mock_response,
        )
        result = await JapaneseConnection.get_data("cat")
        assert "Kanji: 猫" in result
        assert "Hiragana: ねこ" in result


@pytest.mark.asyncio
async def test_get_data_handles_api_error():
    mock_response = {"meta": {"status": 500}, "data": []}
    with aioresponses.aioresponses() as mocked:
        mocked.get(
            "https://jisho.org/api/v1/search/words?keyword=test",
            payload=mock_response,
        )
        result = await JapaneseConnection.get_data("test")
        assert "issue getting the translation" in result


@pytest.mark.asyncio
async def test_get_data_handles_exception():
    with aioresponses.aioresponses() as mocked:
        mocked.get(
            "https://jisho.org/api/v1/search/words?keyword=bad",
            exception=ConnectionError("connection failed"),
        )
        result = await JapaneseConnection.get_data("bad")
        assert "Error" in result
