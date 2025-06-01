# utils/auth.py

def get_access_flags(user: dict, page: str) -> tuple[bool, bool, bool, bool]:
    """
    Returns: (can_view, can_add, can_edit, can_delete)
    Role-based access control for specific pages.
    """
    role = user.get("role", "")

    # Default: No access
    can_view = False
    can_add = False
    can_edit = False
    can_delete = False

    # === Contractors Page Access ===
    if page == "contractors":
        if role in ["Superadmin", "HQ Admin"]:
            can_view = can_add = can_edit = can_delete = True
        elif role == "Site PM":
            can_view = can_add = True
        elif role in ["Site Accountant", "HQ Accountant"]:
            can_view = True

    # === Add more pages here ===
    # Example:
    # if page == "projects":
    #     ...

    return can_view, can_add, can_edit, can_delete
