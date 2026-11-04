"""Contagem de objetos rastreados que cruzam uma linha horizontal."""

from collections import Counter
from dataclasses import dataclass

@dataclass
class Travessia:
    """Registro de um objeto que acabou de cruzar a linha."""

    track_id: int
    classe: str
    direcao: str # descendo ou subindo

class ContadorLinha:
    """Conta objetos rastreados que cruzam uma linha horizontal.

    Cada ID é contado no máximo uma vez, na primeira travessia.
    Isso evita contagens repetidas quando a caixa oscila em cima da linha.
    """
    
    def __init__(self, linha_y: int, classes: set[str]):
        self.linha_y = linha_y
        self.classes = classes
        self.por_classe: Counter[str] = Counter()
        self.por_direcao: Counter[str] = Counter()
        self._historico: dict[int, Counter[str]] = {}
        self._ultima_posicao: dict[int, int] = {}
        self._ids_contados: set[int] = set()

    def atualizar(self, track_id: int, classe: str, cy: int) -> Travessia | None:
        """Registra a posição atual de um objeto.

        Devolve uma Travessia se o objeto acabou de cruzar a linha,
        ou None caso contrário.
        """

        votos = self._historico.setdefault(track_id, Counter())
        votos[classe] += 1
        classe_votada = votos.most_common(1)[0][0]

        y_anterior = self._ultima_posicao.get(track_id)
        self._ultima_posicao[track_id] = cy

        if classe_votada not in self.classes:
            return None

        if y_anterior is None or track_id in self._ids_contados:
            return None
        
        if y_anterior < self.linha_y <= cy:
            direcao = "descendo"
        elif y_anterior > self.linha_y >= cy:
            direcao = "subindo"
        else:
            return None

        self._ids_contados.add(track_id)
        self.por_classe[classe_votada] += 1
        self.por_direcao[direcao] += 1
        return Travessia(track_id, classe_votada, direcao)

    @property
    def total(self) -> int:
        """Total de objetos contados."""
        return sum(self.por_classe.values())


if __name__ == "__main__":
    c = ContadorLinha(linha_y=100, classes={"car", "truck"})

    c.atualizar(1, "car", 80)
    c.atualizar(1, "car", 90)
    c.atualizar(1, "truck", 105)   # cruza como "truck"... deve contar como "car"

    print(c.por_classe)
