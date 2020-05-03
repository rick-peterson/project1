import requests
from flask import redirect, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def pagination(current, last):
    """
    Simple pagination algorithm by Rostyslav Bryzgunov https://gist.github.com/kottenator/9d936eb3e4e3c3e02598
    I re-wrote from JS to python. 
    """
    delta = 2
    left = current - delta
    right = current + delta + 1
    range_list = []
    range_with_dots = []
    l = -1

    for i in range(1, last + 1):
        if i == 1 or i == last or i >= left and i < right:
            range_list.append(i)

    for i in range_list:
        if l != -1:
            if i - l == 2:
                range_with_dots.append(l + 1)
            elif i - l != 1:
                range_with_dots.append('...')
        range_with_dots.append(i)
        l = i

    return range_with_dots


def good_reads(isbn):
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "XCiXWfbUzhFkU1PUaxsmKA", "isbns": isbn})
    return res.json()['books'][0]
