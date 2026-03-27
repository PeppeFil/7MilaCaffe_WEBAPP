from urllib.parse import urlencode


def get_csrf_token(client, path="/login"):
    client.get(path)
    with client.session_transaction() as session:
        return session["_csrf_token"]


def login(client, username, password, next_page=None, follow_redirects=True):
    query_string = ""
    if next_page:
        query_string = f"?{urlencode({'next': next_page})}"

    path = f"/login{query_string}"
    csrf_token = get_csrf_token(client, path)
    return client.post(
        path,
        data={
            "username": username,
            "password": password,
            "csrf_token": csrf_token,
        },
        follow_redirects=follow_redirects,
    )
