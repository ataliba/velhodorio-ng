from pymongo import MongoClient
from difflib import SequenceMatcher
import logging
import os
import random
import re
import unicodedata

# Configura o logger para este arquivo
logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_fragment(text: str) -> str:
    text = (text or "").strip(" \t\n\r.,;:!?\"'")
    text = re.sub(
        r"^(o|a|os|as|um|uma|disco|album|álbum|cd|lp|titulo|título|banda|artista)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip(" \t\n\r.,;:!?\"'")


def _parse_query(consulta: str) -> dict:
    texto = consulta.strip()
    texto_norm = _normalize_text(texto)
    parsed = {
        "raw": texto,
        "normalized": texto_norm,
        "artist": None,
        "title": None,
        "folder": None,
        "random_count": None,
        "random_mode": False,
    }

    if any(token in texto_norm for token in ["aleatorio", "aleatoria", "aleatorios", "aleatorias", "escolhe", "escolha", "sorteia", "sugere", "sugira"]):
        parsed["random_mode"] = True
        number_match = re.search(r"\b(\d{1,2})\b", texto_norm)
        parsed["random_count"] = int(number_match.group(1)) if number_match else 3

    folder_match = re.search(r"(?:estilo|pasta|genero|g[eê]nero)\s+(.+?)(?:$|[,.!?;])", texto, flags=re.IGNORECASE)
    if folder_match:
        parsed["folder"] = _clean_fragment(folder_match.group(1))

    title_match = re.search(r"(?:titulo|t[ií]tulo)\s+(.+?)(?:$|[.!?;])", texto, flags=re.IGNORECASE)
    if title_match:
        parsed["title"] = _clean_fragment(title_match.group(1))

    artist_title_match = re.search(
        r"(?:disco\s+(?:do|da)|album\s+(?:do|da)|[áa]lbum\s+(?:do|da))\s+([^,]+?)\s*,\s*(.+)$",
        texto,
        flags=re.IGNORECASE,
    )
    if artist_title_match:
        parsed["artist"] = _clean_fragment(artist_title_match.group(1))
        parsed["title"] = _clean_fragment(artist_title_match.group(2))
        return parsed

    artist_match = re.search(
        r"(?:disco\s+(?:do|da)|da\s+banda|do\s+artista|artista)\s+(.+?)(?:$|[,.!?;])",
        texto,
        flags=re.IGNORECASE,
    )
    if artist_match:
        parsed["artist"] = _clean_fragment(artist_match.group(1))

    if not parsed["title"]:
        quoted = re.findall(r"['\"]([^'\"]+)['\"]", texto)
        if quoted:
            parsed["title"] = _clean_fragment(quoted[-1])

    if not any([parsed["artist"], parsed["title"], parsed["folder"]]):
        # fallback: tenta interpretar termos curtos como artista/título
        parsed["artist"] = _clean_fragment(texto)
        parsed["title"] = _clean_fragment(texto)

    return parsed


def _format_records(records: list[dict]) -> str:
    return "\n".join(
        f"💿 {record.get('artist')} - {record.get('title')} ({record.get('released')})"
        for record in records
    )


def _resolve_fuzzy_value(values: list[str], target: str | None, threshold: float = 0.72) -> str | None:
    if not target:
        return None

    target_norm = _normalize_text(target)
    candidates = []

    for value in values:
        if not value:
            continue
        score = SequenceMatcher(None, target_norm, _normalize_text(value)).ratio()
        candidates.append((score, value))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, best_value = candidates[0]
    return best_value if best_score >= threshold else None


def consultar_acervo_musical(termo: str):
    """
    Consulta o acervo de discos no MongoDB do Ataliba.

    Aceita linguagem natural para consultas como:
    - "procura um disco do Death"
    - "escolhe 3 titulos aleatorios da colecao no estilo Death Metal"
    - "procure o disco de titulo Symbolic"
    - "veja se eu tenho o disco do Metallica, Garage Days Revisited"
    """
    logger.info(f"🔍 Tool iniciada: Buscando por '{termo}'...")

    try:
        mongo_user = os.getenv("MONGODB_USER")
        mongo_pass = os.getenv("MONGODB_PASS")
        mongo_uri = f"mongodb://{mongo_user}:{mongo_pass}@192.168.68.38:27017/n8n"

        logger.info("🔌 Tentando conectar em: 192.168.68.38:27017")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.server_info()
        logger.info("✅ Conexão estabelecida com sucesso!")

        db = client["n8n"]
        collection = db["DiscogsControl"]

        query_info = _parse_query(termo)
        logger.info(
            "🧠 Consulta interpretada | artist=%s | title=%s | folder=%s | random=%s | qtd=%s",
            query_info["artist"],
            query_info["title"],
            query_info["folder"],
            query_info["random_mode"],
            query_info["random_count"],
        )

        artist = query_info["artist"]
        title = query_info["title"]
        folder = query_info["folder"]

        if query_info["random_mode"] and folder:
            folder_regex = re.escape(folder)
            pool = list(
                collection
                .find({"folder": {"$regex": f"^{folder_regex}$", "$options": "i"}})
                .sort([("artist", 1), ("title", 1)])
            )

            if not pool:
                pool = list(
                    collection
                    .find({"folder": {"$regex": folder_regex, "$options": "i"}})
                    .sort([("artist", 1), ("title", 1)])
                )

            if not pool:
                fuzzy_folder = _resolve_fuzzy_value(collection.distinct("folder"), folder)
                if fuzzy_folder:
                    pool = list(
                        collection
                        .find({"folder": {"$regex": f"^{re.escape(fuzzy_folder)}$", "$options": "i"}})
                        .sort([("artist", 1), ("title", 1)])
                    )

            if not pool:
                return f"Percorri as águas e não encontrei títulos no estilo/pasta '{folder}'."

            quantidade = min(query_info["random_count"] or 3, len(pool))
            selecionados = random.sample(pool, quantidade)
            return (
                f"Escolhi {quantidade} título(s) aleatórios da pasta/estilo '{folder}':\n"
                + _format_records(selecionados)
            )

        if artist and title:
            artist_regex = re.escape(artist)
            title_regex = re.escape(title)

            resultados = list(
                collection
                .find({
                    "artist": {"$regex": f"^{artist_regex}$", "$options": "i"},
                    "title": {"$regex": f"^{title_regex}$", "$options": "i"},
                })
            )

            if not resultados:
                resultados = list(
                    collection
                    .find({
                        "artist": {"$regex": artist_regex, "$options": "i"},
                        "title": {"$regex": title_regex, "$options": "i"},
                    })
                    .sort([("released", 1), ("title", 1)])
                )

            if not resultados:
                fuzzy_artist = _resolve_fuzzy_value(collection.distinct("artist"), artist)
                fuzzy_title = _resolve_fuzzy_value(collection.distinct("title"), title)
                if fuzzy_artist and fuzzy_title:
                    resultados = list(
                        collection.find({
                            "artist": {"$regex": f"^{re.escape(fuzzy_artist)}$", "$options": "i"},
                            "title": {"$regex": f"^{re.escape(fuzzy_title)}$", "$options": "i"},
                        })
                    )

            if not resultados:
                return f"Não encontrei no acervo um disco de '{artist}' com o título '{title}'."

            return (
                f"Encontrei {len(resultados)} disco(s) para artista '{artist}' com título '{title}':\n"
                + _format_records(resultados)
            )

        if artist:
            artist_regex = re.escape(artist)
            resultados = list(
                collection
                .find({"artist": {"$regex": f"^{artist_regex}$", "$options": "i"}})
                .sort([("released", 1), ("title", 1)])
            )

            if not resultados:
                resultados = list(
                    collection
                    .find({"artist": {"$regex": artist_regex, "$options": "i"}})
                    .sort([("released", 1), ("title", 1)])
                )

            if not resultados:
                fuzzy_artist = _resolve_fuzzy_value(collection.distinct("artist"), artist)
                if fuzzy_artist:
                    resultados = list(
                        collection
                        .find({"artist": {"$regex": f"^{re.escape(fuzzy_artist)}$", "$options": "i"}})
                        .sort([("released", 1), ("title", 1)])
                    )

            if not resultados:
                return f"Percorri as águas e não encontrei artista '{artist}' no acervo."

            return (
                f"Encontrei {len(resultados)} disco(s) com artista '{artist}':\n"
                + _format_records(resultados)
            )

        if title:
            title_regex = re.escape(title)
            resultados = list(
                collection
                .find({"title": {"$regex": f"^{title_regex}$", "$options": "i"}})
                .sort([("artist", 1), ("released", 1)])
            )

            if not resultados:
                resultados = list(
                    collection
                    .find({"title": {"$regex": title_regex, "$options": "i"}})
                    .sort([("artist", 1), ("released", 1)])
                )

            if not resultados:
                fuzzy_title = _resolve_fuzzy_value(collection.distinct("title"), title)
                if fuzzy_title:
                    resultados = list(
                        collection
                        .find({"title": {"$regex": f"^{re.escape(fuzzy_title)}$", "$options": "i"}})
                        .sort([("artist", 1), ("released", 1)])
                    )

            if not resultados:
                return f"Percorri as águas e não encontrei título '{title}' no acervo."

            return (
                f"Encontrei {len(resultados)} disco(s) com título '{title}':\n"
                + _format_records(resultados)
            )

        if folder:
            folder_regex = re.escape(folder)
            resultados = list(
                collection
                .find({"folder": {"$regex": f"^{folder_regex}$", "$options": "i"}})
                .sort([("artist", 1), ("title", 1)])
            )

            if not resultados:
                resultados = list(
                    collection
                    .find({"folder": {"$regex": folder_regex, "$options": "i"}})
                    .sort([("artist", 1), ("title", 1)])
                )

            if not resultados:
                fuzzy_folder = _resolve_fuzzy_value(collection.distinct("folder"), folder)
                if fuzzy_folder:
                    resultados = list(
                        collection
                        .find({"folder": {"$regex": f"^{re.escape(fuzzy_folder)}$", "$options": "i"}})
                        .sort([("artist", 1), ("title", 1)])
                    )

            if not resultados:
                return f"Percorri as águas e não encontrei a pasta/estilo '{folder}'."

            return (
                f"Encontrei {len(resultados)} disco(s) na pasta/estilo '{folder}':\n"
                + _format_records(resultados)
            )

        resultados = list(
            collection
            .find({
                "$or": [
                    {"artist": {"$regex": re.escape(termo), "$options": "i"}},
                    {"title": {"$regex": re.escape(termo), "$options": "i"}},
                ]
            })
            .sort([("artist", 1), ("released", 1), ("title", 1)])
        )

        if not resultados:
            fuzzy_artist = _resolve_fuzzy_value(collection.distinct("artist"), termo)
            fuzzy_title = _resolve_fuzzy_value(collection.distinct("title"), termo)

            if fuzzy_artist:
                resultados = list(
                    collection
                    .find({"artist": {"$regex": f"^{re.escape(fuzzy_artist)}$", "$options": "i"}})
                    .sort([("released", 1), ("title", 1)])
                )
            elif fuzzy_title:
                resultados = list(
                    collection
                    .find({"title": {"$regex": f"^{re.escape(fuzzy_title)}$", "$options": "i"}})
                    .sort([("artist", 1), ("released", 1)])
                )

        if not resultados:
            return f"Percorri as águas e não encontrei nada sobre '{termo}'."

        return (
            f"Encontrei {len(resultados)} registro(s) relacionados a '{termo}' em artist/título:\n"
            + _format_records(resultados)
        )

    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO NA TOOL: {type(e).__name__} - {str(e)}")
        return f"Erro técnico na tool: {str(e)}"
