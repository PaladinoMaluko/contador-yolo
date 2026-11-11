"""API HTTP do contador de veículos"""

import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from .processador import CLASSES_PADRAO, processar_video

PASTA_ENTRADAS = Path("uploads")
PASTA_SAIDAS = Path("saidas")

class ResultadoContagem(BaseModel):
    """Contagem de veículos de um video processado"""

    id: str
    total: int
    por_classe: dict[str, int]
    por_direcao: dict[str, int]
    

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
    """Retorna a lista de classes que podem ser contadas"""
    return {"classes": sorted(CLASSES_PADRAO)}

@app.post("/videos")
def enviar_video(
    arquivo: Annotated[UploadFile, File(description="video a ser processado")],
    linha: Annotated[float, Form(description="altura da linha, entre 0 e 1")] = 0.6,
    classes: Annotated[list[str] | None, Form(description="Define quais ou qual veículo será contado")] = None
) -> ResultadoContagem:
    """Recebe um video, conta os veículos que cruzam a linha e devolve a
    contagem"""
    if classes is not None:

        if any(not nome.strip(" ") for nome in classes):
            mensagem = f"Nome de classe não informado"
            raise HTTPException(status_code=400, detail=mensagem)
        
        classes = {nome.lower() for nome in classes}
        invalidas = classes - CLASSES_PADRAO
        if invalidas:
            mensagem = f"Classe(s) inválida(s): {', '.join(sorted(invalidas))}. Classes permitidas:{', '.join(sorted(CLASSES_PADRAO))}"
            raise HTTPException(status_code=400, detail=mensagem)
        

    id_video = uuid.uuid4().hex
    # Só a extensão do nome enviado é aproveitada: o nome inteiro pode conter
    #"../" e fazer o arquivo ser gravado fora da pasta
    sufixo = Path(arquivo.filename or "").suffix.lower()
    entrada = PASTA_ENTRADAS / f"{id_video}{sufixo}"
    saida = PASTA_SAIDAS / f"{id_video}.mp4"

    PASTA_ENTRADAS.mkdir(parents=True, exist_ok=True)
    with entrada.open("wb") as destino:
        shutil.copyfileobj(arquivo.file, destino)

    try:
        contador = processar_video(entrada, saida, linha_proporcao=linha, classes=classes)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    except FileNotFoundError as erro:
        mensagem = "O arquivo enviado não é um vídeo válido"
        raise HTTPException(status_code=400, detail=mensagem) from erro 
    finally:
        # O original não é mais necessário
        # Sem isso, a pasta cresce a cada envio
        entrada.unlink(missing_ok=True)

    return ResultadoContagem(
        id=id_video,
        total=contador.total,
        por_classe=dict(contador.por_classe),
        por_direcao=dict(contador.por_direcao),
    )    


