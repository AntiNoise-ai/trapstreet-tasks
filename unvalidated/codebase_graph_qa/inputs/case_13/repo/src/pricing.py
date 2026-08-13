def calculate_discount(price, code):
    if code == "SAVE10":
        return price * 0.9
    return price
