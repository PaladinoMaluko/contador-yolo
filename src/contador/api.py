"""API HTTP do contador de veículos"""

from fastapi import FastAPI

from .processador import CLASSES_PADRAO

app = FastAPI(
    title="Contador de veículos",
    description="Envie um video e receba a contagem dos veículos que cruzam a linha",
    version="0.1.0"
)

@app.get("/saude")
def saude() -> dict[str, str]:
    """Indica que a API está no ar"""
    return {"status": "ok"}

@app.get("/classes")
def classes() -> dict[str, list[str]]:
    """Retorna a lista de classes que vão ser contadas"""
    return {"classes": sorted(CLASSES_PADRAO)}