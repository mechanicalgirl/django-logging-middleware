import logging
import time

def logging_view_filter(request, view_func, view_args, view_kwargs):
    """
    Decorates a view to log out start and end time, duration, and view count
    """  
    start_time = time.time()
    response = view_func(request, *view_args, **view_kwargs)
    end_time = time.time()
    loc = {'view_func':view_func.__name__, 'time': (end_time - start_time)}
    logging.debug("Processed View: %s.%s in(%0.4f)" %(view_func.__module__, view_func.func_name, loc['time']))
    if hasattr(response, 'view_times'):
        response.view_times.append(loc)
    else:
        response.view_times = [loc]
    return response

def model_decorator(func=None):
    """
    Decorates a model function to return standard logging information
    """
    def decorated(*args, **kwargs):
        start_time = time.time()
        response = func(*args, **kwargs)
        end_time = time.time()
        loc = {'model_func':func.__name__, 'time': (end_time - start_time)}
        logging.debug("Processed Model: %s.%s in(%0.4f)" %(func.__module__, func.func_name, loc['time']))
        return response
    return decorated
