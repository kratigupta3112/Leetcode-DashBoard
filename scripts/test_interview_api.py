"""Probe LeetCode tags for interview experience posts."""
import httpx
import json

HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com/discuss/interview-experience",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

QUERY = """
query discussPostItems($orderBy: ArticleOrderByEnum, $keywords: [String]!, $tagSlugs: [String!], $skip: Int, $first: Int) {
  ugcArticleDiscussionArticles(
    orderBy: $orderBy
    keywords: $keywords
    tagSlugs: $tagSlugs
    skip: $skip
    first: $first
  ) {
    totalNum
    edges {
      node {
        title
        slug
        summary
        createdAt
        topic { id }
        tags { slug name }
      }
    }
  }
}
"""

TAGS = [
    "interview-experience",
    "interview",
    "interview-experiences",
    "interview-question",
    "career",
]


def try_tag(tag: str) -> None:
    payload = {
        "operationName": "discussPostItems",
        "query": QUERY,
        "variables": {
            "orderBy": "MOST_RECENT",
            "keywords": [""],
            "tagSlugs": [tag],
            "skip": 0,
            "first": 3,
        },
    }
    r = httpx.post("https://leetcode.com/graphql", json=payload, headers=HEADERS, timeout=30)
    data = r.json()
    if "errors" in data:
        print(tag, "ERR", data["errors"][0].get("message", "")[:120])
        return
    block = data["data"]["ugcArticleDiscussionArticles"]
    total = block["totalNum"]
    titles = [e["node"]["title"][:70] for e in block["edges"]]
    print(f"{tag}: total={total}")
    for t in titles:
        print("  -", t)


if __name__ == "__main__":
    for tag in TAGS:
        try_tag(tag)
