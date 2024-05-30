from flask import redirect, session
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("id_usuario") is None:
            return redirect("/account/login")
        return f(*args, **kwargs)
    return decorated_function

def rolEmpleado_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("Empleado") is False:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def rolAdmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("Administrador") is False:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function

def rolCliente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("Cliente") is False:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function