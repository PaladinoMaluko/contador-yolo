"""Ponto de entrada da linha de comando: 
python -m contador --entrada ... --saida ..."""

import argparse
import sys

from .contagem import ContadorLinha
from .processador import processar_video, CLASSES_PADRAO

def criar_parser() -> argparse.ArgumentParser:
    """Define os argumentos aceitos pelo comando"""
    parser = argparse.ArgumentParser(
        prog="contador",
        description="Conta os veículos que cruzam uma linha horizontal num vídeo"
    )
    parser.add_argument("--entrada", required=True, 
                        help="vídeo para contagem")
    parser.add_argument("--saida", required=True, 
                        help="vídeo gerado depois da contagem(.mp4 ou .avi)")
    parser.add_argument("--linha", type=float, default=0.6,
                        help="altura da linha, entre 0 e 1, com 0 no topo (padrão: %(default)s)")
    parser.add_argument("--modelo", default="yolo11n.pt",
                        help="pesos do YOLO (padrão: %(default)s)")
    parser.add_argument("--imgsz", type=int, default=480,
                        help="tamanho da imagem na inferência; menor = mais rápido (padrão: %(default)s)")
    parser.add_argument("--classes", nargs="+", default=None, choices=sorted(CLASSES_PADRAO),
                        help="quais tipos de veiculos vão ser contados (nome precisa ser em ingles)")
    return parser

def mostrar_progresso(atual: int, total: int) -> None:
    """Atualizar a mesma linha do terminal com o andamento do processamento"""
    if total > 0:
        texto = f"Processando: {atual}/{total} ({atual / total:.0%})"
    else:
        texto = f"Processando: {atual}"
    print(f"\r{texto}", end="", flush=True)

def mostrar_resumo(contador: ContadorLinha) -> None:
    """Mostra o resultado da contagem dos veiculos"""
    classes = contador.classes
    por_classe = contador.por_classe
    por_direcao = contador.por_direcao
    total = contador.total

    print(f"Total: {total}")
    print(f"Classe(s) que foram contadas: {', '.join(sorted(classes))}")
    for nome, qtd in por_classe.items():
        print(f"{nome} - {qtd}")
    print(f"Desceram: {por_direcao['descendo']} | Subiram: {por_direcao['subindo']}")

def main() -> int:
    """Roda o comando e devolve o codigo de saida (0 = sucesso)"""
    args = criar_parser().parse_args()

    try:
        if args.classes is not None:
            args.classes = set(args.classes)

        contador = processar_video(
            args.entrada,
            args.saida,
            modelo=args.modelo,
            linha_proporcao=args.linha,
            imgsz=args.imgsz,
            classes=args.classes,
            ao_progredir=mostrar_progresso,
        )

    except (FileNotFoundError, ValueError, RuntimeError) as erro:
        # quebra de linha(\n), o progresso pode estar aberto
        print(f"\nErro: {erro}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelado pelo usuario", file=sys.stderr)
        return 130
    
    print()
    mostrar_resumo(contador)
    return 0 

if __name__ == "__main__":
    sys.exit(main())