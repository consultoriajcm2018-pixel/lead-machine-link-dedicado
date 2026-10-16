"""Linha de comando: sincronizar e exportar."""

from __future__ import annotations

import argparse
import json

import datetime as dt

from . import store
from .sync import sincronizar


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="leiloes")
    parser.add_argument("comando", choices=["sync", "listar"])
    parser.add_argument("--db", default=None)
    parser.add_argument("--paginas", type=int, default=6)
    parser.add_argument("--detalhes", type=int, default=60)
    parser.add_argument("--body", default="suv",
                        help="carrocerias separadas por virgula (suv, crossover, picape)")
    parser.add_argument("--tier", default=None)
    parser.add_argument("--uf", default=None)
    parser.add_argument("--incluir-sem-uf", action="store_true")
    parser.add_argument("--preco-max", type=float, default=None)
    parser.add_argument("--teto-solar", action="store_true")
    parser.add_argument("--idade-max", type=int, default=5,
                        help="anos de uso maximos do veiculo (padrao 5)")
    parser.add_argument("--incluir-sem-ano", action="store_true",
                        help="tambem lista lotes sem ano modelo declarado")
    parser.add_argument("--limite", type=int, default=50)
    args = parser.parse_args(argv)

    if args.comando == "sync":
        print(json.dumps(sincronizar(args.db, args.paginas, args.detalhes), ensure_ascii=False, indent=2))
        return 0

    conn = store.connect(args.db)
    try:
        linhas = store.buscar(
            conn,
            body=[b.strip() for b in args.body.split(",") if b.strip()],
            tier=args.tier,
            uf=args.uf,
            incluir_sem_uf=args.incluir_sem_uf,
            preco_max=args.preco_max,
            teto_solar=args.teto_solar,
            ano_min=dt.date.today().year - args.idade_max if args.idade_max is not None else None,
            incluir_sem_ano=args.incluir_sem_ano,
            limite=args.limite,
        )
    finally:
        conn.close()
    print(json.dumps(linhas, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
