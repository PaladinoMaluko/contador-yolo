"""API HTTP do contador de veículos"""
import uuid
from pathlib import Path
from typing import Annotated, Literal
from dataclasses import dataclass
import time

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .processador import CLASSES_PADRAO, processar_video, validar_linha

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

PASTA_DADOS = Path("dados_api")
PASTA_ENTRADAS = PASTA_DADOS / "entradas"
PASTA_SAIDAS = PASTA_DADOS / "saidas"

TAMANHO_MAXIMO = 200 * 1024 * 1024  # 200 MB


Situacao = Literal["na_fila", "processando", "concluido", "erro"]

class Contagem(BaseModel):
    """Totais de veiculos que cruzaram a linha"""

    total: int
    por_classe: dict[str, int]
    por_direcao: dict[str, int]

class StatusTarefa(BaseModel):
    """O que o cliente recebe ao enviar ou consultar um video"""

    id: str
    situacao: Situacao
    progresso: float
    contagem: Contagem | None = None
    erro: str | None = None
    url_video: str | None = None
    url_status: str | None = None

@dataclass
class Tarefa:
    """Estado interno de um video enviado para processamento"""

    id: str
    situacao: Situacao = "na_fila"
    progresso: float = 0.0
    contagem: Contagem | None = None
    erro: str | None = None

tarefas: dict[str, Tarefa] = {}


def _limpar_pastas() -> None:
    """Apaga os arquivos de execuções anteriores da API

    As tarefas ficam em memória: depois de um reinício, nenhum arquivo antigo
    pode mais ser consultado ou baixado
    """
    for pasta in (PASTA_ENTRADAS, PASTA_SAIDAS):
        pasta.mkdir(parents=True, exist_ok=True)
        for arquivo in pasta.iterdir():
            if arquivo.is_file():
                arquivo.unlink()

@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    """Prepara a API ao iniciar e libera os recursos ao desligar"""
    _limpar_pastas()
    yield
    # Os vídeos que ainda estão na fila são cancelados e o que está
    # processando não pode ser interrompido no meio
    executor.shutdown(wait=False, cancel_futures=True)

# Um vídeo por vez: o YOLO já ocupa a CPU toda, e vários em paralelo
# ficariam todos lentos e disputando memória
executor = ThreadPoolExecutor(max_workers=1)

app = FastAPI(
    title="Contador de veículos",
    description="Envie um video e receba a contagem dos veículos que cruzam a linha",
    version="0.1.0",
    lifespan=ciclo_de_vida
)

def _processar_tarefa(
        tarefa: Tarefa,
        entrada: Path,
        saida: Path,
        linha: float,
        classes: set[str] | None
) -> None:
    """Processa o video numa thread do executor e registra o resultado na tarefa"""
    tarefa.situacao = "processando"

    def ao_progredir(atual: int, total: int) -> None:
        if total > 0:
            tarefa.progresso = atual / total

    start = time.perf_counter()
    try:
        logger.info("Tarefa iniciada %s", tarefa.id)
        contador = processar_video(
            entrada, saida, linha_proporcao=linha, classes=classes,
            ao_progredir=ao_progredir
        )
    except FileNotFoundError as erro:
        logger.warning("Tarefa %s: video inválido (%s)", tarefa.id, erro)
        tarefa.situacao = "erro"
        tarefa.erro = "O arquivo enviado não é um video válido"
    except Exception:
        # caso um erro ocorre-se, a exceção desapareceria em silêncio dentro da thread, 
        # e a tarefa ficaria em “processando” para sempre 
        logger.exception("Falha ao processar o video %s", tarefa.id)
        tarefa.situacao = "erro"
        tarefa.erro = "Erro interno ao processar o video"
    else:
        end = time.perf_counter()
        tarefa.contagem = Contagem(
            total=contador.total,
            por_classe=dict(contador.por_classe),
            por_direcao=dict(contador.por_direcao)
        )
        tarefa.progresso = 1.0
        tarefa.situacao = "concluido"
        total_tempo = end - start
        logger.info("Tarefa %s concluida: %d veiculos em %.1fs", tarefa.id, contador.total, total_tempo)
    finally:
        entrada.unlink(missing_ok=True)
        if tarefa.situacao != "concluido":
            saida.unlink(missing_ok=True)


def _montar_status(request: Request, tarefa: Tarefa) -> StatusTarefa:
    """Converte o estado interno da tarefa na resposta publica"""
    url_video = None
    url_status = str(request.url_for("consultar_video", id_video=tarefa.id))
    if tarefa.situacao == "concluido":
        url_video = str(request.url_for("baixa_video", id_video=tarefa.id))

    return StatusTarefa(
        id=tarefa.id,
        situacao=tarefa.situacao,
        progresso=round(tarefa.progresso, 3),
        contagem=tarefa.contagem,
        erro=tarefa.erro,
        url_video=url_video,
        url_status=url_status
    )

@app.get("/saude")
def saude() -> dict[str, str]:
    """Indica que a API está no ar"""
    return {"status": "ok"}

@app.get("/classes")
def classes() -> dict[str, list[str]]:
    """Retorna a lista de classes que podem ser contadas"""
    return {"classes": sorted(CLASSES_PADRAO)}

@app.get("/videos/{id_video}/anotado")
def baixa_video(id_video: str) -> FileResponse:
    """Devolve o vídeo anotado de um processamento concluído."""
    tarefa = tarefas.get(id_video)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    # Durante o processamento, o arquivo já existe no disco, mas está pela metade
    if tarefa.situacao in ("na_fila", "processando"):
        mensagem = (
            f"O vídeo ainda não está pronto ({tarefa.situacao}, {tarefa.progresso:.0%}). "
            "Consulte o status e tente de novo depois."
        )
        raise HTTPException(status_code=409, detail=mensagem)

    if tarefa.situacao == "erro":
        mensagem = f"O processamento falhou, e não há vídeo anotado: {tarefa.erro}"
        raise HTTPException(status_code=404, detail=mensagem)

    caminho = PASTA_SAIDAS / f"{id_video}.mp4"
    # A tarefa terminou, mas o arquivo pode ter sido apagado depois (limpeza da 5.5)
    if not caminho.is_file():
        raise HTTPException(status_code=410, detail="O vídeo anotado não está mais disponível")

    return FileResponse(
        caminho,
        media_type="video/mp4",
        filename=f"contagem_{id_video}.mp4",
    )

@app.get("/videos/{id_video}")
def consultar_video(request: Request, id_video: str) -> StatusTarefa:
    """Devolve a situação e, quando pronto, a contagem de um video enviado"""
    tarefa = tarefas.get(id_video)
    if tarefa is None:
        raise HTTPException(status_code=404, detail="Video não encontrado")
    return _montar_status(request, tarefa)

@app.post("/videos", status_code=202)
def enviar_video(
    request: Request,
    arquivo: Annotated[UploadFile, File(description="video a ser processado")],
    linha: Annotated[float, Form(description="altura da linha, entre 0 e 1")] = 0.6,
    classes: Annotated[list[str] | None, Form(description="Define quais ou qual veículo será contado")] = None,
) -> StatusTarefa:
    """Recebe um video, enfileira o video e devolve o status"""
    try:
        linha = validar_linha(linha)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro
    
    if classes is not None:

        if any(not nome.strip() for nome in classes):
            mensagem = f"Nome de classe não informado"
            raise HTTPException(status_code=400, detail=mensagem)
        
        classes = {nome.lower().strip() for nome in classes}
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
    contar_byte = 0
    with entrada.open("wb") as destino:
        while True:
            pedaco = arquivo.file.read(1024 * 1024) # 1 MB por vez
            if not pedaco:
                break
            contar_byte += len(pedaco)
            if contar_byte > TAMANHO_MAXIMO:
                entrada.unlink(missing_ok=True)
                limite_atual = TAMANHO_MAXIMO // (1024 * 1024)

                logger.warning("Limite de MB (%s) ultrapassado %s", limite_atual, id_video)
                raise HTTPException(status_code=413, detail=f"Limite de MB ({limite_atual}) ultrapassado")

            destino.write(pedaco)

    tarefa = Tarefa(id=id_video)
    tarefas[id_video] = tarefa

    logger.info("Tarefa recebida: %s", tarefa.id)

    executor.submit(_processar_tarefa, tarefa, entrada, saida, linha, classes)
    return _montar_status(request, tarefa)

