from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from config.settings import settings
from ..core.session_manager import session_manager

router = APIRouter()


@router.post("/human")
async def human(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid', 0)
        if not session_manager.session_exists(sessionid):
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        if params.get('interrupt'):
            session_manager.interrupt_session(sessionid)

        if params['type'] == 'echo':
            session_manager.put_text(sessionid, params['text'])
        elif params['type'] == 'chat':
            session_manager.handle_chat(sessionid, params['text'])

        return JSONResponse(
            content={"code": 0, "msg": "ok"}
        )
    except KeyError as e:
        return JSONResponse(
            status_code=200,
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={"code": -1, "msg": str(e)}
        )


@router.post("/humanaudio")
async def humanaudio(request: Request):
    try:
        form = await request.form()
        sessionid = int(form.get('sessionid', '0'))
        if not session_manager.session_exists(sessionid):
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        fileobj = form["file"]
        filename = fileobj.filename
        filebytes = await fileobj.read()
        session_manager.put_audio(sessionid, filebytes)

        return JSONResponse(
            content={"code": 0, "msg": "ok"}
        )
    except KeyError as e:
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )


@router.post("/set_audiotype")
async def set_audiotype(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid', 0)
        if not session_manager.session_exists(sessionid):
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        session_manager.set_audio_type(sessionid, params['audiotype'], params['reinit'])

        return JSONResponse(
            content={"code": 0, "msg": "ok"}
        )
    except KeyError as e:
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )


@router.post("/record")
async def record(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid', 0)
        if not session_manager.session_exists(sessionid):
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        if params['type'] == 'start_record':
            session_manager.start_recording(sessionid)
        elif params['type'] == 'end_record':
            session_manager.stop_recording(sessionid)

        return JSONResponse(
            content={"code": 0, "msg": "ok"}
        )
    except KeyError as e:
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )


@router.post("/interrupt_talk")
async def interrupt_talk(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid', 0)
        if not session_manager.session_exists(sessionid):
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        session_manager.interrupt_session(sessionid)

        return JSONResponse(
            content={"code": 0, "msg": "ok"}
        )
    except KeyError as e:
        return JSONResponse(
            status_code=200,
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )


@router.post("/is_speaking")
async def is_speaking(request: Request):
    try:
        params = await request.json()

        sessionid = params.get('sessionid', 0)
        if not session_manager.session_exists(sessionid):
            return JSONResponse(
                status_code=200,
                content={"code": -1, "msg": f"Session {sessionid} not found"}
            )

        speaking = session_manager.is_speaking(sessionid)
        return JSONResponse(
            content={"code": 0, "data": speaking}
        )
    except KeyError as e:
        return JSONResponse(
            content={"code": -1, "msg": f"Session not found: {e}"}
        )
    except Exception as e:
        return JSONResponse(
            content={"code": -1, "msg": str(e)}
        )


@router.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket, sessionid: int = 0):
    await websocket.accept()

    try:
        if sessionid == 0:
            sessionid = int(websocket.query_params.get('sessionid', 0))

        if not session_manager.session_exists(sessionid):
            await websocket.send_json({"code": -1, "msg": f"Session {sessionid} not found"})
            await websocket.close()
            return

        while True:
            try:
                audio_data = await websocket.receive_bytes()

                session_manager.put_audio(sessionid, audio_data)

                await websocket.send_json({"code": 0, "msg": "ok"})

            except WebSocketDisconnect:
                break
            except Exception as e:
                await websocket.send_json({"code": -1, "msg": str(e)})

    except Exception as e:
        pass
    finally:
        pass
