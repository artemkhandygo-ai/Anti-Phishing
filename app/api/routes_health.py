from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Проверка состояния сервиса",
    description="Возвращает простой ответ, если API запущено и отвечает.",
)
def health():
    return {"status": "ok"}
