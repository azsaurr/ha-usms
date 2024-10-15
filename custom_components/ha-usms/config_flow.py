"""Config flow for HA-USMS."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from usms import USMSAccount, USMSLoginError

from .const import DOMAIN, LOGGER

USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT,
            ),
        ),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.PASSWORD,
            ),
        ),
    }
)


class HaUsmsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA-USMS integration."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> data_entry_flow.FlowResult:
        """Handle the initial step."""
        _errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except USMSLoginError as error:
                LOGGER.exception(error)
                _errors["base"] = error
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_DATA_SCHEMA, errors=_errors
        )

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        await self.hass.async_add_executor_job(USMSAccount, username, password)
