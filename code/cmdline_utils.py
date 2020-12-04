"""Utility functions
"""

def yes_no(msg):
    """Simple yes/no command line prompt"""
    resp = None
    while resp is None:
        text = input(msg)
        text = text.strip().lower()
        if text in ["y", "yes", "yup", "absolutely"]:
            resp = True
        elif text in ["n", "no", "nope", "cancel"]:
            resp = False
        else:
            resp = None
    return resp
