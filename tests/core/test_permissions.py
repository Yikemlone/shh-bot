from core.permissions import is_guild_owner, user_has_role, is_moderator


class TestIsGuildOwner:
    def test_owner_returns_true(self, mock_interaction):
        mock_interaction.user.id = 12345
        mock_interaction.guild.owner_id = 12345
        assert is_guild_owner(mock_interaction)

    def test_non_owner_returns_false(self, mock_interaction):
        mock_interaction.user.id = 99999
        mock_interaction.guild.owner_id = 12345
        assert not is_guild_owner(mock_interaction)


class TestUserHasRole:
    def test_matching_role_returns_true(self, mock_interaction):
        role = type("Role", (), {"name": "Spammer"})()
        mock_interaction.user.roles = [role]
        assert user_has_role(mock_interaction, "Spammer")

    def test_case_insensitive_match(self, mock_interaction):
        role = type("Role", (), {"name": "spammer"})()
        mock_interaction.user.roles = [role]
        assert user_has_role(mock_interaction, "Spammer")

    def test_no_matching_role_returns_false(self, mock_interaction):
        role = type("Role", (), {"name": "Moderator"})()
        mock_interaction.user.roles = [role]
        assert not user_has_role(mock_interaction, "Spammer")


class TestIsModerator:
    def test_manage_messages_granted(self, mock_member):
        mock_member.guild_permissions.manage_messages = True
        assert is_moderator(mock_member)

    def test_no_perms_returns_false(self, mock_member):
        assert not is_moderator(mock_member)

    def test_kick_members_granted(self, mock_member):
        mock_member.guild_permissions.kick_members = True
        assert is_moderator(mock_member)
