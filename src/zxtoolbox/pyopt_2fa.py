import pyotp

key = 'AEZRYWYPJBYLTGYC7OXFVF6ROBAVLUHW'
totp = pyotp.TOTP(key)
print(totp.now())