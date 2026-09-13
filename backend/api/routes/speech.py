import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from backend.speech import (
    MAX_AUDIO_BYTES,
    InvalidAudio,
    TranscriptionUnavailable,
    transcribe_audio,
)

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


@router.post("/transcribe")
async def transcribe(audio: Annotated[UploadFile, File(...)]):
    try:
        data = await audio.read(MAX_AUDIO_BYTES + 1)
    finally:
        await audio.close()
    if not data:
        raise HTTPException(400, "沒有收到錄音，請再錄一次。")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(413, "錄音太大，請分段說明。")
    try:
        text = await run_in_threadpool(transcribe_audio, data)
    except InvalidAudio as exc:
        raise HTTPException(422, str(exc)) from exc
    except TranscriptionUnavailable as exc:
        logger.exception("Speech recognition initialization failed")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(500, "語音轉文字暫時失敗，請再試一次。") from exc
    return {"text": text}
