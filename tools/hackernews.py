import html
import logging
import re

import requests

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
DEFAULT_LIMIT = 5
MAX_SCAN = 100


def _parse_query(consulta: str) -> dict:
    texto = (consulta or "").strip()
    texto_norm = texto.lower()

    category = "top"
    for key, aliases in {
        "top": ["top", "tops", "principais", "melhores do momento", "frontpage"],
        "best": ["best", "melhores", "mais bem votadas"],
        "new": ["new", "novas", "recentes", "latest", "ultimas", "últimas"],
        "ask": ["ask", "ask hn"],
        "show": ["show", "show hn"],
        "job": ["job", "jobs", "vaga", "vagas"],
    }.items():
        if any(alias in texto_norm for alias in aliases):
            category = key
            break

    limit_match = re.search(r"\b(\d{1,2})\b", texto_norm)
    limit = int(limit_match.group(1)) if limit_match else DEFAULT_LIMIT
    limit = max(1, min(limit, 15))

    query = None
    for pattern in [
        r"(?:sobre|de|com|busque|buscar|procure|procurar|pesquise|pesquisar)\s+(.+)$",
        r"['\"]([^'\"]+)['\"]",
    ]:
        match = re.search(pattern, texto, flags=re.IGNORECASE)
        if match:
            query = match.group(1).strip(" \t\n\r.,;:!?\"'")
            break

    return {"category": category, "limit": limit, "query": query}


def _fetch_json(path: str):
    response = requests.get(f"{HN_API_BASE}/{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def _fetch_item(item_id: int) -> dict | None:
    try:
        item = _fetch_json(f"item/{item_id}.json")
        if not item or item.get("deleted") or item.get("dead"):
            return None
        return item
    except requests.RequestException as exc:
        logger.warning("⚠️ Falha ao buscar item %s do Hacker News: %s", item_id, exc)
        return None


def _format_item(item: dict) -> str:
    title = html.unescape(item.get("title") or "(sem título)")
    author = item.get("by", "desconhecido")
    score = item.get("score", 0)
    comments = item.get("descendants", 0)
    item_id = item.get("id")
    url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
    return f"- {title} | por {author} | {score} pontos | {comments} comentários | {url}"


def consultar_hackernews(consulta: str):
    """
    Consulta o Hacker News por ranking ou termo nos títulos.

    Exemplos:
    - "top 5 do hacker news"
    - "best do hacker news"
    - "ask hn sobre python"
    - "procure no hacker news sobre postgres"
    """
    logger.info("📰 Tool Hacker News iniciada: %s", consulta)

    try:
        parsed = _parse_query(consulta)
        logger.info(
            "🧠 Hacker News interpretado | categoria=%s | limite=%s | query=%s",
            parsed["category"],
            parsed["limit"],
            parsed["query"],
        )

        endpoint = {
            "top": "topstories.json",
            "best": "beststories.json",
            "new": "newstories.json",
            "ask": "askstories.json",
            "show": "showstories.json",
            "job": "jobstories.json",
        }[parsed["category"]]

        story_ids = _fetch_json(endpoint) or []
        if not story_ids:
            return "As águas do Hacker News vieram vazias agora."

        items = []
        scan_limit = MAX_SCAN if parsed["query"] else parsed["limit"] * 3

        for item_id in story_ids[:scan_limit]:
            item = _fetch_item(item_id)
            if not item:
                continue

            title = html.unescape(item.get("title") or "")
            if parsed["query"] and parsed["query"].lower() not in title.lower():
                continue

            items.append(item)
            if len(items) >= parsed["limit"]:
                break

        if not items:
            if parsed["query"]:
                return (
                    f"Não encontrei histórias no Hacker News sobre '{parsed['query']}' "
                    f"na categoria '{parsed['category']}'."
                )
            return f"Não encontrei histórias na categoria '{parsed['category']}' do Hacker News."

        titulo_categoria = {
            "top": "top",
            "best": "best",
            "new": "new",
            "ask": "Ask HN",
            "show": "Show HN",
            "job": "Jobs",
        }[parsed["category"]]

        if parsed["query"]:
            header = (
                f"Encontrei {len(items)} história(s) no Hacker News sobre "
                f"'{parsed['query']}' em '{titulo_categoria}':"
            )
        else:
            header = f"Aqui estão {len(items)} história(s) de '{titulo_categoria}' no Hacker News:"

        return header + "\n" + "\n".join(_format_item(item) for item in items)

    except requests.RequestException as exc:
        logger.error("❌ Erro ao consultar Hacker News: %s", exc)
        return "Não consegui atravessar a correnteza até o Hacker News agora."
    except Exception as exc:
        logger.error("❌ Erro crítico na tool Hacker News: %s", exc)
        return f"Erro técnico na tool Hacker News: {exc}"
