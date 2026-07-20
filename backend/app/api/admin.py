from fastapi import APIRouter
from app.services.storage import get_all_chat_messages

router = APIRouter()

def _get_paired_logs():
    messages = get_all_chat_messages()
    sessions = {}
    for msg in reversed(messages):
        sid = msg["session_id"]
        if sid not in sessions:
            sessions[sid] = []
        sessions[sid].append(msg)
        
    paired_logs = []
    for sid, msgs in sessions.items():
        i = 0
        while i < len(msgs):
            if msgs[i]["role"] == "user":
                u_msg = msgs[i]
                a_msg = msgs[i+1] if i+1 < len(msgs) and msgs[i+1]["role"] == "assistant" else None
                paired_logs.append({
                    "id": str(u_msg["id"]),
                    "session_id": sid,
                    "user_message": u_msg["content"],
                    "ai_response": a_msg["content"] if a_msg else "",
                    "timestamp": u_msg["timestamp"]
                })
                i += 2 if a_msg else 1
            else:
                i += 1
                
    paired_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return paired_logs

@router.get("/analytics/logs")
async def get_logs(page: int = 1, limit: int = 50):
    """Lấy lịch sử chat có phân trang."""
    logs = _get_paired_logs()
    
    start = (page - 1) * limit
    end = start + limit
    
    return {
        "total": len(logs),
        "page": page,
        "limit": limit,
        "data": logs[start:end]
    }

@router.get("/analytics/stats")
async def get_stats():
    """Lấy thống kê cơ bản."""
    logs = _get_paired_logs()
    
    stats_by_date = {}
    for log in logs:
        date = log.get("timestamp", "").split("T")[0] if log.get("timestamp") else "unknown"
        stats_by_date[date] = stats_by_date.get(date, 0) + 1
        
    return {
        "total_interactions": len(logs),
        "by_date": stats_by_date
    }

