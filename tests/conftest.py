import pytest


@pytest.fixture
def mock_interaction(mocker):
    interaction = mocker.Mock()
    interaction.user.id = 12345
    interaction.user.global_name = "TestUser"
    interaction.user.roles = []
    interaction.user.guild_permissions = mocker.Mock(
        manage_messages=False, kick_members=False, ban_members=False, administrator=False
    )
    interaction.guild.owner_id = 12345
    interaction.guild.get_member.return_value = None
    return interaction


@pytest.fixture
def mock_member(mocker):
    member = mocker.Mock()
    member.id = 67890
    member.guild_permissions = mocker.Mock(
        manage_messages=False, kick_members=False, ban_members=False, administrator=False
    )
    return member
