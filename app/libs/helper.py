import string
import secrets

def generate_string(n):
    letters_digits = string.ascii_letters + string.digits
    result = ""
    for i in range(n):
        result += secrets.choice(letters_digits)

    return result