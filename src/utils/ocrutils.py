from typing import Optional, Self
from ddddocr import DdddOcr
from PIL import Image

class OcrUtils:
    _instance: Optional[Self] = None

    # ocr libs
    _dddd_ocr = DdddOcr(show_ad=False, use_gpu=False)

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def read_code(self, image: Image) -> Optional[str]:
        code = self._dddd_ocr.classification(image)
        return code if type(code) == str else None 
