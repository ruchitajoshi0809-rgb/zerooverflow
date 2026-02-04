def predict_overflow(fill_level, hours_since_last_collection):
    if fill_level >= 80 and hours_since_last_collection >= 6:
        return True
    return False
