import pytest
from core.exceptions import on_command_errors


@pytest.mark.asyncio
async def test_on_command_errors_logs_and_sends(mocker):
    interaction = mocker.Mock()
    interaction.command.name = "test"
    interaction.response.is_done.return_value = False
    interaction.response.send_message = mocker.AsyncMock()
    error = type("FakeError", (Exception,), {"__str__": lambda s: "test error"})()
    await on_command_errors(interaction, error)
    interaction.response.send_message.assert_awaited_once()
