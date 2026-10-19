from fastapi import FastAPI
import uvicorn
from api.handlers import router
from api.device import router as device_router
from api.user import router as user_router
from fastapi.staticfiles import StaticFiles


app = FastAPI(
    title="Калькулятор тока для автомобильных устройств",
    version="1.0.0",
    servers=[{
        "url":"http://127.0.0.1:8000"
    }],
    description=(
        "Веб-сервис расчета тока для автомобильных устройств.\n\n"
        "**Без авторизации** доступно только чтение: список услуг (с фильтром) "
        "и лента публикаций, а также регистрация и вход.\n\n"
        "**С авторизацией** (cookie-сессия в Redis, кнопка Authorize или "
        "заголовок Cookie) — методы создателя: создание услуги с картинкой/видео, "
        "получение полей черновика, публикация, удаление, лайк, выход.\n\n"
        "Сессия хранится в Redis (`session:{sid}` → id пользователя, TTL 1 час), "
        "в браузер ставится HttpOnly-cookie `session_id`."
    ),
    openapi_tags=[
        {
            "name": "Аутентификация",
            "description": "Регистрация, вход (cookie-сессия в Redis), выход, текущий пользователь.",
        },
        {
            "name": "Услуги",
            "description": (
                "Операции с устройствами/услугами. "
                "Чтение списка и ленты доступно без авторизации; "
                "создание, черновик, публикация, удаление и лайк требуют cookie."
            ),
        },
    ],
)

app.include_router(router)
app.include_router(device_router)
app.include_router(user_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
