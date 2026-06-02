"""Fetch discussion posts from LeetCode GraphQL."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from salarytracker.config import BATCH_SIZE, GRAPHQL_URL

LIST_QUERY = {
    "operationName": "discussPostItems",
    "query": (
        "query discussPostItems($orderBy: ArticleOrderByEnum, $keywords: [String]!, "
        "$tagSlugs: [String!], $skip: Int, $first: Int) {\n"
        "  ugcArticleDiscussionArticles(\n"
        "    orderBy: $orderBy\n"
        "    keywords: $keywords\n"
        "    tagSlugs: $tagSlugs\n"
        "    skip: $skip\n"
        "    first: $first\n"
        "  ) {\n"
        "    totalNum\n"
        "    pageInfo { hasNextPage }\n"
        "    edges {\n"
        "      node {\n"
        "        title\n"
        "        slug\n"
        "        summary\n"
        "        createdAt\n"
        "        updatedAt\n"
        "        hitCount\n"
        "        topicId\n"
        "        topic { id topLevelCommentCount }\n"
        "        reactions { count reactionType }\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}"
    ),
}

DETAIL_QUERY = {
    "operationName": "discussPostDetail",
    "query": (
        "query discussPostDetail($topicId: ID!) {\n"
        "  ugcArticleDiscussionArticle(topicId: $topicId) {\n"
        "    title\n"
        "    content\n"
        "    summary\n"
        "    createdAt\n"
        "    topicId\n"
        "    slug\n"
        "  }\n"
        "}"
    ),
}

COMPENSATION_TAG = "compensation"
INTERVIEW_TAG = "interview-experience"


def _headers_for_tag(tag_slug: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Referer": f"https://leetcode.com/discuss/{tag_slug}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }


def _reaction_count(reactions: list[dict[str, Any]], reaction_type: str) -> int:
    for reaction in reactions:
        if reaction.get("reactionType") == reaction_type:
            return int(reaction.get("count") or 0)
    return 0


def _post_graphql(
    client: httpx.Client, payload: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    import json

    response = client.post(GRAPHQL_URL, json=payload, headers=headers)
    response.raise_for_status()
    body = response.json()
    if "errors" in body:
        raise RuntimeError(json.dumps(body["errors"], indent=2))
    return body["data"]


def fetch_post_page(
    skip: int = 0,
    first: int = BATCH_SIZE,
    tag_slug: str = COMPENSATION_TAG,
) -> tuple[list[dict[str, Any]], int]:
    headers = _headers_for_tag(tag_slug)
    payload = {
        **LIST_QUERY,
        "variables": {
            "orderBy": "MOST_RECENT",
            "keywords": [""],
            "tagSlugs": [tag_slug],
            "skip": skip,
            "first": first,
        },
    }
    with httpx.Client(timeout=30.0, headers=headers) as client:
        data = _post_graphql(client, payload, headers)
    articles = data["ugcArticleDiscussionArticles"]
    nodes = [edge["node"] for edge in articles["edges"]]
    return nodes, int(articles["totalNum"])


def _to_record(node: dict[str, Any]) -> dict[str, Any]:
    reactions = node.get("reactions") or []
    slug = node.get("slug") or ""
    topic_id = int(node["topic"]["id"])
    return {
        "id": topic_id,
        "title": node.get("title") or "",
        "summary": node.get("summary") or "",
        "slug": slug,
        "url": f"https://leetcode.com/discuss/post/{topic_id}",
        "created_at": node.get("createdAt"),
        "updated_at": node.get("updatedAt"),
        "hits": node.get("hitCount") or 0,
        "comment_count": node.get("topic", {}).get("topLevelCommentCount") or 0,
        "upvotes": _reaction_count(reactions, "UPVOTE"),
        "downvotes": _reaction_count(reactions, "THUMBS_DOWN"),
    }


async def _fetch_content(
    client: httpx.AsyncClient, post: dict[str, Any], headers: dict[str, str]
) -> None:
    payload = {**DETAIL_QUERY, "variables": {"topicId": str(post["id"])}}
    response = await client.post(GRAPHQL_URL, json=payload, headers=headers)
    response.raise_for_status()
    body = response.json()
    article = body["data"]["ugcArticleDiscussionArticle"]
    post["content"] = article.get("content") or ""
    if not post.get("title"):
        post["title"] = article.get("title") or ""
    if article.get("slug"):
        post["slug"] = article["slug"]
        post["url"] = f"https://leetcode.com/discuss/post/{post['id']}/{article['slug']}"


async def enrich_posts(posts: list[dict[str, Any]], tag_slug: str = COMPENSATION_TAG) -> None:
    if not posts:
        return
    headers = _headers_for_tag(tag_slug)
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        await asyncio.gather(
            *[_fetch_content(client, post, headers) for post in posts]
        )


def list_recent_posts(
    skip: int = 0, first: int = BATCH_SIZE, tag_slug: str = COMPENSATION_TAG
) -> list[dict[str, Any]]:
    nodes, _ = fetch_post_page(skip=skip, first=first, tag_slug=tag_slug)
    return [_to_record(node) for node in nodes]
