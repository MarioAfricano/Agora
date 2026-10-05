from app.security import hash_password, verify_password


def test_hash_is_not_the_password():
    password_hash = hash_password("TestingPass1212")
    assert password_hash != "TestingPass1212"


def test_verify_password_accepts_the_right_password():
    password_hash = hash_password("TestingPass1212")
    assert verify_password("TestingPass1212", password_hash)


def test_verify_password_rejects_a_wrong_password():
    password_hash = hash_password("TestingPass1212")
    assert not verify_password("NotTestingPass1212", password_hash)


def test_same_password_gives_different_hashes():
    password_hash = hash_password("TestingPass1212")
    password_hash2 = hash_password("TestingPass1212")
    assert password_hash != password_hash2
