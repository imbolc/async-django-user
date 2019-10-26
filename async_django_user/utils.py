import secrets
import string


def get_random_string(
    length=12, allowed_chars=string.ascii_letters + string.digits
):
    return "".join(secrets.choice(allowed_chars) for i in range(length))
