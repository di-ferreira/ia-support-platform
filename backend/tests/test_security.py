from app.core.security import create_tokens, decode_token


def test_create_tokens_emits_typ_claims():
    tokens = create_tokens(user_id=1, perfil="admin")
    access = decode_token(tokens["access_token"])
    refresh = decode_token(tokens["refresh_token"])
    assert access["typ"] == "access"
    assert refresh["typ"] == "refresh"
    assert access["sub"] == "1"
    assert refresh["sub"] == "1"
