"""Funções que desenham as anotações (caixas, linha
painel) nos frames recebidos."""

from dataclasses import dataclass

import cv2
import numpy as np
from .contagem import ContadorLinha


# Cores comaptiveis do OpenCV (BGR)
VERDE = (0, 255, 0)
VERMELHO = (0, 0, 255)
AZUL = (255, 0, 0)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)
AMARELO = (0, 255, 255)

CORES_CLASSES = {
    "car": VERDE,
    "truck": VERMELHO,
    "bus": AZUL
}

# frozen=True torna nossa classe imutavel para evitar alterações
@dataclass(frozen=True)
class Estilo:
    """Medidas visuais proporcionais a resolução do 
    video"""

    escala: float
    tam_fonte: float
    espessura: int

def criar_estilo(largura: int) -> Estilo:
    """Calcula o estilo a partir da largura do video"""
    escala = largura / 1280

    return Estilo(
        escala=escala,
        tam_fonte=1.6 * escala,
        espessura=max(1, round(2 * escala)),
    )

def _desenhar_rotulo(frame: np.ndarray, texto: str, x: int, y: int, 
                    cor: tuple[int, int, int], estilo: Estilo) -> None:
    """Escreve o texto sobre um fundo colorido, logo
    acima do ponto (x, y)"""
    fonte = cv2.FONT_HERSHEY_SIMPLEX
    (larg_txt, alt_txt), base = cv2.getTextSize(
        texto, fonte, estilo.tam_fonte, estilo.espessura
    )

    # Limita a caixa ao tomo do frame
    y_texto = max(y - int(8 * estilo.escala), alt_txt + base)
    
    cv2.rectangle(frame, (x, y_texto - alt_txt - base), (x + larg_txt, y_texto + base), 
                  cor, cv2.FILLED,)
    
    cv2.putText(frame, texto, (x, y_texto), fonte, estilo.tam_fonte, PRETO, 
                estilo.espessura)

def desenhar_veiculo(frame: np.ndarray, cx: int, cy: int, 
                     caixa: tuple[int, int, int, int], track_id: int, classe: str, 
                     confianca: float, estilo: Estilo,) -> None:
    """Desenha a caixa, o rotulo "#id classe conf" e
     o centro do veiculo"""
    x1, y1, x2, y2 = caixa
    cor = CORES_CLASSES.get(classe, BRANCO)

    cv2.rectangle(frame, (x1, y1), (x2, y2), cor, estilo.espessura)
    _desenhar_rotulo(frame, f"#{track_id} {classe} {confianca:.2f}", 
                     x1, y1, cor, estilo)
    
    cv2.circle(frame, (cx, cy), 4 * estilo.espessura, cor, cv2.FILLED)

def desenhar_linha(frame: np.ndarray, linha_y: int, estilo: Estilo) -> None:
    """Desenha a linha que conta os veiculos"""
    espessura = estilo.espessura
    largura = frame.shape[1]
    cv2.line(frame, (0, linha_y), (largura, linha_y), AMARELO, espessura)

def desenhar_painel(frame: np.ndarray, contador: ContadorLinha, 
                    estilo: Estilo) -> None:
    """Desenha o total de veiculos contados"""
    escala = estilo.escala
    espessura = estilo.espessura
    tam_font = estilo.tam_fonte
    # Defini em qual altura a linha deve ficar
    altura_linha = int(50 * escala)
    
    contagem = contador.por_classe
    total = contador.total

    # Desenha o nome e quantidade um embaixo do outro
    for i, (nome, qtd) in enumerate(contagem.items()):
        y = altura_linha * (i + 2)
        cv2.putText(frame, f"{nome} - {qtd}", (20, y), 
                    cv2.FONT_HERSHEY_SIMPLEX, tam_font, AMARELO, 
                    espessura + 1)
   
    cv2.putText(frame, f"Total: {total}", (20, altura_linha), 
                cv2.FONT_HERSHEY_SIMPLEX, tam_font, AMARELO, 
                espessura + 1)
    
