USE_HTTPS = False

def get_use_https():
    return USE_HTTPS

def set_use_https(value: bool):
    global USE_HTTPS
    USE_HTTPS = value