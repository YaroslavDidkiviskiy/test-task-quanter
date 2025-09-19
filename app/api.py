# app/api.py
import os, json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from .models import DealConfig, EngineState
from .exchange import ExchangeClient
from .engine import DealEngine
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Trading Engine (Testnet)", version="0.4.1")

state = EngineState()
ex = ExchangeClient(
    api_key=os.getenv("BYBIT_API_KEY", ""),
    secret=os.getenv("BYBIT_SECRET", ""),
    market_type=os.getenv("MARKET_TYPE", "swap"),
    testnet=True,
)
engine = DealEngine(ex, state, poll_interval=float(os.getenv("POLL_INTERVAL", "2.0")))
ROOT = os.path.dirname(__file__)

@app.api_route("/", methods=["GET", "POST", "DELETE"])
async def root(request: Request):
    try:
        if request.method == "GET":
            accept = request.headers.get("accept", "")
            if ("text/html" in accept) and ("application/json" not in accept) and (request.query_params.get("json") is None):
                return FileResponse(os.path.join(ROOT, "static", "index.html"))
            try:
                payload = state.model_dump()
            except Exception:
                payload = state.dict()
            try:
                bal = await ex.fetch_balance()
                payload["free_usdt"] = ex.get_free_usdt(bal)
            except Exception:
                pass
            return JSONResponse(payload)

        if request.method == "DELETE":
            await engine.stop()
            return {"status": "stopped"}

        if state.running:
            raise HTTPException(400, "Engine already running")

        cfg: DealConfig | None = None
        ctype = request.headers.get("content-type", "")
        if "multipart/form-data" in ctype:
            form = await request.form()
            up = form.get("file")
            if not up:
                raise HTTPException(400, "No 'file' in multipart form")
            data = json.loads((await up.read()).decode("utf-8"))
            cfg = DealConfig(**data)
        else:
            body = (await request.body()).decode("utf-8").strip()
            if body:
                data = json.loads(body)
                cfg = DealConfig(**data)

        if cfg is None:
            cfg_path = os.getenv("CONFIG_PATH", "config.json")
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cfg = DealConfig(**data)
            except Exception as e:
                raise HTTPException(400, f"No config provided and failed to load {cfg_path}: {type(e).__name__}: {e}")

        await engine.start(cfg)
        return {"status": "started", "position": state.position}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, detail=f"{type(e).__name__}: {e}")

@app.on_event("shutdown")
async def _shutdown():
    await engine.stop()
    await ex.close()
