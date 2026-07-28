from __future__ import annotations

from gui.pptx_service import (
    convert_pdf, libreoffice_available, render_pdf_thumbnails,
    thumbnail_rendering_available,
)


class PdfService:
    libreoffice_available = staticmethod(libreoffice_available)
    thumbnail_rendering_available = staticmethod(thumbnail_rendering_available)
    convert = staticmethod(convert_pdf)
    thumbnails = staticmethod(render_pdf_thumbnails)
