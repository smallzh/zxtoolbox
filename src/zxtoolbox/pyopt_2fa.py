import pyotp


def parseTotpCdoe(key):
    """ 解析 totp 的 code码

    Args:
        key: 认证码
    """
    totp = pyotp.TOTP(key)
    print(totp.now())


if __name__ == "__main__":
    key = ''
    parseTotpCdoe(key)
