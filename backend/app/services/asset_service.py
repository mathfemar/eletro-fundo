from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..schemas import AssetCreate, AssetResponse, AssetUpdate


ASSET_QUERY = text(
    """
    SELECT
        a.ID_ATIVO AS id_ativo,
        a.CD_ATIVO AS cd_ativo,
        COALESCE(m.CD_YF, '') AS cd_yf,
        COALESCE(a.PRECO_ONLINE, 0) AS preco_online,
        COALESCE(TRIM(a.MOEDA), 'BRL') AS moeda,
        COALESCE(a.FATOR_PRECO, 1) AS fator_preco,
        (
            SELECT h.VL_CLOSE FROM APP_ATIVO_PRECO_HIST h
            WHERE h.ID_ATIVO = a.ID_ATIVO
            ORDER BY h.DT_PRECO DESC
            LIMIT 1
        ) AS last_close,
        (
            SELECT h.VL_ADJ_CLOSE FROM APP_ATIVO_PRECO_HIST h
            WHERE h.ID_ATIVO = a.ID_ATIVO
            ORDER BY h.DT_PRECO DESC
            LIMIT 1
        ) AS last_adj_close
    FROM DIM_ATIVO a
    LEFT JOIN DIM_ATIVO_MAPPING m ON m.ID_ATIVO = a.ID_ATIVO
    WHERE (:only_online = 0 OR COALESCE(a.PRECO_ONLINE, 0) = 1)
      AND (:only_mapped = 0 OR COALESCE(m.CD_YF, '') <> '')
    ORDER BY a.CD_ATIVO
    """
)


class AssetService:
    def list_assets(self, session: Session, only_online: bool = False, only_mapped: bool = False) -> list[AssetResponse]:
        rows = session.execute(ASSET_QUERY, {'only_online': int(only_online), 'only_mapped': int(only_mapped)}).mappings().all()
        return [
            AssetResponse(
                id_ativo=row['id_ativo'],
                cd_ativo=row['cd_ativo'],
                cd_yf=row['cd_yf'] or None,
                preco_online=bool(row['preco_online']),
                moeda=(row['moeda'] or 'BRL').strip(),
                fator_preco=float(row['fator_preco']) if row['fator_preco'] is not None else 1.0,
                last_close=float(row['last_close']) if row['last_close'] is not None else None,
                last_adj_close=float(row['last_adj_close']) if row['last_adj_close'] is not None else None,
            )
            for row in rows
        ]

    def get_online_mapped_assets(self, session: Session) -> list[dict]:
        rows = session.execute(
            text(
                """
                SELECT a.ID_ATIVO AS asset_id, a.CD_ATIVO AS asset_code, m.CD_YF AS ticker
                FROM DIM_ATIVO a
                INNER JOIN DIM_ATIVO_MAPPING m ON m.ID_ATIVO = a.ID_ATIVO
                WHERE COALESCE(a.PRECO_ONLINE, 0) = 1
                  AND COALESCE(m.CD_YF, '') <> ''
                ORDER BY a.ID_ATIVO
                """
            )
        ).mappings().all()
        return [dict(row) for row in rows]

    def create_asset(self, session: Session, payload: AssetCreate) -> AssetResponse:
        asset_code = payload.cd_ativo.strip().upper()
        yf_code = payload.cd_yf.strip().upper() if payload.cd_yf else None

        existing = session.execute(
            text(
                """
                SELECT a.ID_ATIVO AS id_ativo
                FROM DIM_ATIVO a
                WHERE UPPER(TRIM(a.CD_ATIVO)) = :asset_code
                LIMIT 1
                """
            ),
            {'asset_code': asset_code},
        ).mappings().first()
        if existing:
            raise ValueError('Ativo já cadastrado')

        next_id = session.execute(text('SELECT COALESCE(MAX(ID_ATIVO), 0) + 1 FROM DIM_ATIVO')).scalar_one()
        session.execute(
            text(
                """
                INSERT INTO DIM_ATIVO (
                    ID_ATIVO,
                    CD_ATIVO,
                    MOEDA,
                    PRECO_ONLINE,
                    FATOR_PRECO
                ) VALUES (
                    :id_ativo,
                    :cd_ativo,
                    :moeda,
                    :preco_online,
                    :fator_preco
                )
                """
            ),
            {
                'id_ativo': next_id,
                'cd_ativo': asset_code,
                'moeda': payload.moeda.strip().upper(),
                'preco_online': int(payload.preco_online),
                'fator_preco': payload.fator_preco,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO DIM_ATIVO_MAPPING (
                    ID_ATIVO,
                    CD_ATIVO,
                    CD_YF
                ) VALUES (
                    :id_ativo,
                    :cd_ativo,
                    :cd_yf
                )
                """
            ),
            {
                'id_ativo': next_id,
                'cd_ativo': asset_code,
                'cd_yf': yf_code,
            },
        )
        session.flush()
        return AssetResponse(
            id_ativo=next_id,
            cd_ativo=asset_code,
            cd_yf=yf_code,
            preco_online=payload.preco_online,
            moeda=payload.moeda.strip().upper(),
            fator_preco=payload.fator_preco,
        )

    def update_asset(self, session: Session, asset_id: int, payload: AssetUpdate) -> AssetResponse:
        existing = session.execute(
            text(
                """
                SELECT ID_ATIVO
                FROM DIM_ATIVO
                WHERE ID_ATIVO = :asset_id
                LIMIT 1
                """
            ),
            {'asset_id': asset_id},
        ).mappings().first()
        if not existing:
            raise ValueError('Ativo não encontrado')

        asset_code = payload.cd_ativo.strip().upper()
        yf_code = payload.cd_yf.strip().upper() if payload.cd_yf else None

        duplicated = session.execute(
            text(
                """
                SELECT ID_ATIVO
                FROM DIM_ATIVO
                WHERE UPPER(TRIM(CD_ATIVO)) = :asset_code
                  AND ID_ATIVO <> :asset_id
                LIMIT 1
                """
            ),
            {'asset_code': asset_code, 'asset_id': asset_id},
        ).mappings().first()
        if duplicated:
            raise ValueError('Já existe outro ativo com este código')

        session.execute(
            text(
                """
                UPDATE DIM_ATIVO
                SET CD_ATIVO = :cd_ativo,
                    MOEDA = :moeda,
                    PRECO_ONLINE = :preco_online,
                    FATOR_PRECO = :fator_preco
                WHERE ID_ATIVO = :asset_id
                """
            ),
            {
                'asset_id': asset_id,
                'cd_ativo': asset_code,
                'moeda': payload.moeda.strip().upper(),
                'preco_online': int(payload.preco_online),
                'fator_preco': payload.fator_preco,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO DIM_ATIVO_MAPPING (ID_ATIVO, CD_ATIVO, CD_YF)
                VALUES (:asset_id, :cd_ativo, :cd_yf)
                ON CONFLICT(ID_ATIVO) DO UPDATE SET
                    CD_ATIVO = excluded.CD_ATIVO,
                    CD_YF = excluded.CD_YF
                """
            ),
            {
                'asset_id': asset_id,
                'cd_ativo': asset_code,
                'cd_yf': yf_code,
            },
        )
        session.flush()
        return AssetResponse(
            id_ativo=asset_id,
            cd_ativo=asset_code,
            cd_yf=yf_code,
            preco_online=payload.preco_online,
            moeda=payload.moeda.strip().upper(),
            fator_preco=payload.fator_preco,
        )
