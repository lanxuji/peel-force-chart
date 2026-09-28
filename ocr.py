import base64
import requests
import os


def ocr_image_b64(image_base64, mode="placeholder"):
    """调用 OCR 识别图片，返回文本行列表"""
    if mode == "placeholder":
        return ["聚酯薄膜", "型号: TB1", "规格: 75μm×1091mm×4050m", "净重: 461.6kg", "卷号: H260828B08C16N", "内电晕"]

    elif mode == "tencent":
        try:
            from tencentcloud.common import credential
            from tencentcloud.common.profile.client_profile import ClientProfile
            from tencentcloud.common.profile.http_profile import HttpProfile
            from tencentcloud.ocr.v20181119 import ocr_client, models
        except ImportError:
            return ["未安装腾讯云SDK，请在 requirements.txt 添加 tencentcloud-sdk-python"]

        secret_id = os.environ.get("TENCENT_SECRET_ID", "")
        secret_key = os.environ.get("TENCENT_SECRET_KEY", "")
        if not secret_id or not secret_key:
            return ["未配置腾讯云密钥：请在 Streamlit Cloud Secrets 里设置 TENCENT_SECRET_ID / TENCENT_SECRET_KEY"]

        try:
            cred = credential.Credential(secret_id, secret_key)
            http_profile = HttpProfile()
            http_profile.endpoint = "ocr.tencentcloudapi.com"
            client_profile = ClientProfile()
            client_profile.httpProfile = http_profile
            client = ocr_client.OcrClient(cred, "ap-guangzhou", client_profile)

            req = models.GeneralBasicOCRRequest()
            req.ImageBase64 = image_base64
            resp = client.GeneralBasicOCR(req)

            lines = []
            for item in resp.TextDetections:
                if getattr(item, "DetectedText", ""):
                    lines.append(item.DetectedText)
            return lines
        except Exception as e:
            return [f"腾讯云OCR错误: {e}"]

    elif mode == "ocrspace":
        url = "https://api.ocr.space/parse/image"
        payload = {
            'base64Image': f'data:image/jpeg;base64,{image_base64}',
            'OCREngine': 2,
            'language': 'chi_sim'
        }
        try:
            resp = requests.post(url, data=payload, timeout=30)
            result = resp.json()
            if result.get('IsErroredOnProcessing'):
                return [f"OCR错误: {result.get('ErrorMessage')}"]
            lines = []
            for page in result.get('ParsedResults', []):
                lines.extend(page.get('ParsedText', '').strip().split('\n'))
            return [l.strip() for l in lines if l.strip()]
        except Exception as e:
            return [f"OCR异常: {e}"]

    elif mode == "local":
        try:
            import pytesseract
            from PIL import Image
            import io
            img_data = base64.b64decode(image_base64)
            img = Image.open(io.BytesIO(img_data))
            text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            return [l.strip() for l in text.split('\n') if l.strip()]
        except ImportError:
            return ["请安装: pip install pytesseract pillow"]
        except Exception as e:
            return [f"本地OCR异常: {e}"]

    return []


def ocr_image(image_bytes, mode="placeholder"):
    """从图片 bytes 识别"""
    img_b64 = base64.b64encode(image_bytes).decode()
    return ocr_image_b64(img_b64, mode)
