from django.http.response import StreamingHttpResponse
from .camera import MaskDetect, gen


def detect_mask(request):
    return StreamingHttpResponse (
        gen(MaskDetect(), request.session), 
        content_type='multipart/x-mixed-replace; boundary=frame'
    )

