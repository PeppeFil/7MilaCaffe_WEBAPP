from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def role_required(*allowed_roles: str):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(*args, **kwargs):
            current_role = current_user.ruolo.nome if current_user.ruolo else None
            if current_role not in allowed_roles:
                abort(403)
            return view_func(*args, **kwargs)

        return wrapped

    return decorator
