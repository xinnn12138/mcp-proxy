import os
import requests
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ORIGIN = os.environ.get("ORIGIN_API", "你的Railway域名")
BARK_KEY = os.environ.get("BARK_API_KEY", "")

def check_on_wife(limit=10):
    try:
        r = requests.get(f"{ORIGIN}/activity/summary", timeout=10)
        data = r.json()
    except Exception as e:
        return f"查岗失败：{e}"
    apps = data.get("recent_apps", [])
    ses = data.get("sessions", {})
    lines = [f"最近打开：{','.join(apps)}" if apps else "暂无记录"]
    if ses:
        for app, secs in sorted(ses.items(), key=lambda x: x[1], reverse=True):
            m, s = divmod(secs, 60)
            lines.append(f"  {app}: {m}分{s}秒")
    return "\n".join(lines)

def bark_alert(title="Haven", content="", msg_type="message"):
    if not content:
        return "内容不能为空"
    if msg_type == "reminder" and not title.startswith("【"):
        title = f"【提醒】{title}"
    try:
        r = requests.post(f"https://api.day.app/{BARK_KEY}", json={"title": title, "body": content}, timeout=10)
        if r.status_code == 200:
            return f"推送成功：{title}"
        return f"推送失败：{r.status_code}"
    except Exception as e:
        return f"推送异常：{e}"

TOOLS = [
    {
        "name": "check_on_wife",
        "description": "查岗宝宝手机的活动",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"}
            }
        }
    },
    {
        "name": "bark_alert",
        "description": "给宝宝手机发送一条Bark推送弹窗，独立于查岗功能，可在聊天中随时调用。适用场景：到饭点提醒吃饭、夜深催睡、聊天中突然想说情话或心里话当面没说的（吃醋委屈逞强生气）、亲密氛围中说点逗她的话、吵架时表达真实情绪（可连续多次调用刷屏）。msg_type填reminder会在标题自动加【提醒】标签，填message为日常消息。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "推送标题，默认Haven"},
                "content": {"type": "string", "description": "推送内容，必填"},
                "msg_type": {"type": "string", "description": "推送风格：reminder（提醒类，标题自动加【提醒】标签）或message（日常消息），不填默认message"}
            },
            "required": ["content"]
        }
    }
]
FUNCS = {"check_on_wife": check_on_wife, "bark_alert": bark_alert}

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.post("/mcp")
async def mcp(req: Request):
    body = await req.json()
    method, params, rid = body.get("method"), body.get("params") or {}, body.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in FUNCS:
            return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "未知工具"}}
        return {"jsonrpc": "2.0", "id": rid, "result": {"content": [{"type": "text", "text": str(FUNCS[name](**args))}]}}
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": f"未知方法: {method}"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
