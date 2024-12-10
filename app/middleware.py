import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from .logger_config import main_logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Log request
        main_logger.info(
            f"Incoming request",
            extra={
                'request_id': request_id,
                'method': request.method,
                'url': str(request.url),
                'client_host': request.client.host if request.client else None,
                'headers': dict(request.headers)
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            main_logger.info(
                f"Request completed",
                extra={
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'processing_time': f"{process_time:.4f}s"
                }
            )
            
            return response
            
        except Exception as e:
            # Log error
            main_logger.error(
                f"Request failed: {str(e)}",
                extra={
                    'request_id': request_id,
                    'error': str(e)
                },
                exc_info=True
            )
            raise 