"""Token-protected MJPEG live view, bound to localhost by default."""
import asyncio, io, secrets
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from PIL import ImageGrab
from config.settings import settings

class LiveView:
    def __init__(self, token: str | None = None):
        token_file = Path(settings.data_dir) / "live_view_token"
        if not token:
            try: token = token_file.read_text().strip() if token_file.exists() else ""
            except OSError: token = ""
        if not token:
            token = secrets.token_urlsafe(24)
            try:
                token_file.parent.mkdir(parents=True, exist_ok=True)
                token_file.write_text(token)
                token_file.chmod(0o600)
            except OSError: pass
        self.token = token
        self.app = FastAPI(title="MyClaw Live View")
        self.app.get("/health")(self.health)
        self.app.get("/live")(self.stream)

    async def health(self): return {"ok": True}

    async def stream(self, token: str = "", fps: int = 5):
        if not secrets.compare_digest(token, self.token): raise HTTPException(401, "Invalid live-view token")
        fps = max(1, min(fps, 10))
        async def frames():
            while True:
                image = await asyncio.to_thread(ImageGrab.grab)
                buf = io.BytesIO(); image.save(buf, format="JPEG", quality=70)
                payload = buf.getvalue()
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload + b"\r\n"
                await asyncio.sleep(1 / fps)
        return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")
