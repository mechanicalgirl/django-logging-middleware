import logging, time
import django
from django.db import connection
from django.conf import settings
import re, sys, traceback
from middleware import logging_decorators

class SqlLoggingList(list):

    def append(self, object):
        writere = re.compile('insert|update|delete', re.IGNORECASE)
        readre = re.compile('select', re.IGNORECASE)
        if writere.search(object['sql']):
            object['type'] = 'write'
        elif readre.search(object['sql']):
            object['type'] = 'read'
        else:
            object['type'] = 'unknown'

        logging.debug('(%s|%s) %s' %(object['time'], object['type'], object['sql']))
        
        list.append(self, object)

class LoggingMiddleware(object):

    def log_request(self, request, level=logging.DEBUG):
        try:
            remote = request.META['REMOTE_ADDR']
        except KeyError:
            remote = 'no remote addr'
            
        logging.log(level, '%s Request to %s for %s' %(request.method, request.path, remote))
        
        if request.GET:
            params = '{'+','.join([k+':'+request.GET.get(k, '') for k, v in request.GET.iteritems()])+'}'
            logging.log(level, 'GET Params: %s' %params)
        elif request.POST:
            params = '{'+','.join([k+':'+request.POST.get(k, '') for k, v in request.POST.iteritems()])+'}'
            logging.log(level, 'POST Params: %s' %params)

    def process_request(self, request):
        request.logging_start_time = time.time()
        
        if settings.DEBUG:
            connection.queries = SqlLoggingList(connection.queries)
            
        self.log_request(request)

    def process_response(self, request, response):
        response.logging_end_time = time.time()
        response.logging_start_time = request.logging_start_time
        response.logging_elapsed_time =  (response.logging_end_time - response.logging_start_time)
        
        counts = {'read':0, 'write':0, 'unknown':0}
        for query in connection.queries:
            if 'type' in query:
                counts[query['type']] = counts[query['type']] + 1
            else:
                query['type'] = 'read'
                counts['read'] = 1
            
        if not settings.DEBUG:
            return response
        
        closing_log = 'Completed in %0.4f (%u reqs/sec)' %(response.logging_elapsed_time, (1 / response.logging_elapsed_time))
        
        if hasattr(response, 'view_times'):
            response.views_count = len(response.view_times)
            response.views_time = sum(map(lambda q: float(q['time']), response.view_times))
            response.views_percentage = (response.views_time / response.logging_elapsed_time) * 100
            closing_log += " | Views: %d in %0.4f (%%%0.2f)" %(response.views_count, response.views_time, response.views_percentage)
        
        response.query_count = len(connection.queries)
        response.query_time = sum(map(lambda q: float(q['time']), connection.queries))
        response.query_percentage = (response.query_time / response.logging_elapsed_time) * 100
        closing_log += " | DB: %d in %0.4f (%%%0.2f)" %(response.query_count, response.query_time, response.query_percentage)
        
        types_log = ""
        for type, num in counts.iteritems():
            if num > 0:
                types_log += "%ss:%d" %(type, num)
        if types_log:
            closing_log += '('+types_log+')'
            
        closing_log += " | Status: %d [%s]" %(response.status_code, request.build_absolute_uri())
        logging.debug(closing_log)

        return response
    
    def process_exception(self, request, exception):
        logging.warn(traceback.format_exc(5))
        logging.critical('Exception: %s "%s"' %(exception.__class__, exception.__str__()))
        self.log_request(request, logging.CRITICAL)
        
