from __future__ import annotations

from .services import account_display_name, account_initials


def account_menu(request) -> dict:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "account_display_name": "",
            "account_initials": "",
        }
    return {
        "account_display_name": account_display_name(user),
        "account_initials": account_initials(user),
    }
