"""Junta vídeo, detecção, contagem e desenho num único processamento."""

from collections.abc import Callable
from pathlib import Path

from ultralytics import YOLO

from .contagem import ContadorLinha

from .desenhar import criar_estilo 
from .desenhar import desenhar_linha, desenhar_painel, desenhar_veiculo

from .video import abrir_video, criar_gravador

CLASSES_PADRAO = {"car", "truck", "bus", "motorcycle"}

def processar_video(entrada: str | Path, 
                    saida: str | Path, 
                    modelo: str = "yolo11n.pt", 
                    linha_proporcao: float = 0.6, 
                    classes: set[str] | None = None,
                    imgsz: int = 480,
                    ao_progredir: Callable[[int, int], None] | None = None
                    ) -> ContadorLinha:
    """Detecta, rastreia e conta os veículos de um vídeo, gravando a versão anotada.

    Args:
        entrada: vídeo de origem.
        saida: vídeo anotado a ser criado (.mp4 ou .avi).
        modelo: pesos do YOLO.
        linha_proporcao: altura da linha de contagem, entre 0 e 1 (0 = topo).
        classes: classes a contar; None usa CLASSES_PADRAO.
        imgsz: tamanho da imagem usado na inferência (menor = mais rápido).
        ao_progredir: chamada a cada frame com (frame_atual, total_frames).

    Returns:
        O contador com os totais por classe e por direção.
    """
    if linha_proporcao <= 0 or linha_proporcao >= 1:
        raise ValueError(f"linha_y({linha_proporcao}) com valores incorretos (fora do escopo de 0 e 1)")

    if classes is None:
        classes = set(CLASSES_PADRAO)

    yolo = YOLO(modelo)
    captura, info = abrir_video(entrada)
    gravador = None

    try:
        gravador = criar_gravador(saida, info)
        estilo = criar_estilo(info.largura)
        linha_y = int(info.altura * linha_proporcao)
        contador = ContadorLinha(linha_y, classes)

        num_frame = 0
        while True:
            ok, frame = captura.read()
            if not ok:
                break
            num_frame += 1

            resultado = yolo.track(frame, persist=True, tracker="bytetrack.yaml",
                                   imgsz=imgsz, verbose=False)[0]
            
            for caixa in resultado.boxes:
                if caixa.id is None:
                    continue

                x1, y1, x2, y2 = map(int, caixa.xyxy[0])
                class_id = int(caixa.cls[0])
                confianca = float(caixa.conf[0])
                nome = yolo.names[class_id]
                track_id = int(caixa.id[0])

                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                desenhar_veiculo(frame, cx, cy, (x1, y1, x2, y2), track_id, nome,
                                 confianca, estilo)
                contador.atualizar(track_id, nome, cy)

            desenhar_linha(frame, linha_y, estilo)
            desenhar_painel(frame, contador, estilo)
            gravador.write(frame)

            if ao_progredir is not None:
                ao_progredir(num_frame, info.total_frames)

    finally:
        captura.release()
        # Caso o gravador tenha sido criado, feche o gravador
        if gravador is not None:
            gravador.release()

    return contador