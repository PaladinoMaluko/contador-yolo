"""Funções para ler e gravar arquivos de vídeo."""

from dataclasses import dataclass
from pathlib import Path

import cv2

CODECS = {
    ".mp4": "mp4v",
    ".avi": "MJPG"
}


@dataclass
class InfoVideo:
    """Propriedades basicas de um vídeo"""

    largura: int
    altura: int
    fps: float
    total_frames: int

    @property
    def duracao(self) -> float | None:
        """Devolve a duração do vídeo"""
        if self.fps <= 0:
            return None
        return self.total_frames / self.fps


def abrir_video(caminho: str | Path) -> tuple[cv2.VideoCapture, InfoVideo]:
    """Abre um vídeo para leitura.
    

    Devolve a captura e as propriedades do vídeo.
    Levanta "FileNotFoundError" se o vídeo não puder ser aberto.
    """

    captura = cv2.VideoCapture(str(caminho))
    if not captura.isOpened():
        raise FileNotFoundError(f"Não foi possível abrir o vídeo: {caminho}")

    info = InfoVideo(
        largura=int(captura.get(cv2.CAP_PROP_FRAME_WIDTH)),
        altura=int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        fps=captura.get(cv2.CAP_PROP_FPS),
        total_frames=int(captura.get(cv2.CAP_PROP_FRAME_COUNT))
    )
    return captura, info

def criar_gravador(caminho: str | Path, info: InfoVideo) -> cv2.VideoWriter:
    """Cria um gravador de vídeo com o mesmo tamanho e FPS do original.

    O codec é escolhido pela extensão do arquivo, e a pasta de destino
    é criada se não existir.
    Levanta ValueError para extensões não suportadas.
    """

    caminho = Path(caminho)
    extensao = caminho.suffix.lower()
    if extensao not in CODECS:
        suportadas = ", ".join(CODECS)
        raise ValueError(f"Extensão não suportada: {extensao}. Use alguma dessas: {suportadas}")

    caminho.parent.mkdir(parents=True, exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*CODECS[extensao])
    gravador = cv2.VideoWriter(
        str(caminho), fourcc, info.fps, (info.largura, info.altura)
    )

    # O OpenCV não avisa quando falha ao criar o arquivo, então checamos manualmente.
    if not gravador.isOpened():
        raise RuntimeError(f"Não foi possível criar o vídeo: {caminho}")
    return gravador