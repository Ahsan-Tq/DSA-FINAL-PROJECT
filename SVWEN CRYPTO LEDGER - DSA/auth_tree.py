def authorize(is_authenticated):
    if is_authenticated:
        return True
    else:
        return False
