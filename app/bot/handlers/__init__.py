from aiogram import Router
from .start import router as start_router
from .text_analysis import router as text_router
from .callback import router as callback_router

main_router = Router()
main_router.include_router(start_router)
main_router.include_router(text_router)
main_router.include_router(callback_router)

router = main_router
__all__ = ["router", "start_router", "text_router", "callback_router"]
